import numpy as np
from datetime import datetime
from django.utils import timezone
import pytz
from io import BytesIO, open
from ftplib import FTP
from netCDF4 import Dataset
import gzip
from scipy.interpolate import interp1d
from api.models import Station, Radiosonde, UpdateRecord
import warnings
warnings.filterwarnings("ignore")



def winds_to_UV(windSpeeds, windDirection):
    u = [];  v = []
    for i,wdir in enumerate(windDirection):
        rad = 4.0*np.arctan(1)/180.
        u.append(-windSpeeds[i] * np.sin(rad*wdir))
        v.append(-windSpeeds[i] * np.cos(rad*wdir))
    return np.array(u), np.array(v)


def basic_qc(Ps, T, Td, U, V):
    # remove the weird entries that give TOA pressure at the start of the array
    Ps = np.round(Ps[np.where(Ps>100)], 2)
    T = np.round(T[np.where(Ps>100)], 2)
    Td = np.round(Td[np.where(Ps>100)], 2)
    U = np.round(U[np.where(Ps>100)], 2)
    V = np.round(V[np.where(Ps>100)], 2)

    U[np.isnan(U)] = -9999
    V[np.isnan(V)] = -9999
    Td[np.isnan(Td)] = -9999
    T[np.isnan(T)] = -9999
    Ps[np.isnan(Ps)] = -9999

    if T.size != 0:
        if T[0]<200 or T[0]>330 or np.isnan(T).all():
            Ps = np.array([]); T = np.array([]); Td = np.array([])
            U = np.array([]); V = np.array([])
      
    if not isinstance(Ps, list):
        Ps = Ps.tolist()
    if not isinstance(T, list):
        T = T.tolist()
    if not isinstance(Td, list):
        Td = Td.tolist()
    if not isinstance(U, list):
        U = U.tolist()
    if not isinstance(V, list):
        V = V.tolist()

    return Ps, T, Td, U, V


def RemNaN_and_Interp(raob):
    P_allstns = []; T_allstns = []; Td_allstns = []; times_allstns = []
    U_allstns = []; V_allstns = [];  wmo_ids_allstns = []

    for i,stn in enumerate(raob['Psig']):

        Ps = raob['Psig'][i]
        Ts = raob['Tsig'][i]
        Tds = raob['Tdsig'][i]
        Tm = raob['Tman'][i]
        Tdm = raob['Tdman'][i]
        Pm = raob['Pman'][i]
        Ws = raob['Wspeed'][i]
        Wd = raob['Wdir'][i]

        if len(Pm)>10 and len(Ps)>10:
            u, v = winds_to_UV(Ws, Wd)

            PmTm = zip(Pm, Tm)
            PsTs = zip(Ps, Ts)
            PmTdm = zip(Pm, Tdm)
            PsTds = zip(Ps, Tds)

            PT=[]; PTd = []
            for pmtm in PmTm:
                PT.append(pmtm)
            for psts in PsTs:
                PT.append(psts)
            for pmtdm in PmTdm:
                PTd.append(pmtdm)
            for pstds in PsTds:
                PTd.append(pstds)


            PT = [x for x in PT if all(i == i for i in x)]
            PTd = [x for x in PTd if all(i == i for i in x)]

            PT = sorted(PT, key=lambda x: x[0])
            PT = PT[::-1]
            PTd = sorted(PTd, key=lambda x: x[0])
            PTd = PTd[::-1]

            if len(PT)!=0 and len(PTd)>10:
                P, T = zip(*PT)
                Ptd, Td = zip(*PTd)
                P = np.array(P)
                P = P.astype(int)
                T = np.array(T)
                Td = np.array(Td)

                f = interp1d(Ptd, Td, kind='linear', fill_value="extrapolate")
                Td = f(P)
                Td[P<Ptd[-1]] = np.nan
                f = interp1d(Pm, u, kind='linear', fill_value="extrapolate")
                U = f(P)
                U[P<Pm[-1]] = np.nan
                f = interp1d(Pm, v, kind='linear', fill_value="extrapolate")
                V = f(P)
                V[P<Pm[-1]] = np.nan

                Pqc, Tqc, Tdqc, Uqc, Vqc = basic_qc(P, T, Td, U, V)

                if len(Pqc)!=0:
                    P_allstns.append(Pqc)
                    T_allstns.append(Tqc)
                    Td_allstns.append(Tdqc)
                    U_allstns.append(Uqc)
                    V_allstns.append(Vqc)
                    wmo_ids_allstns.append(raob['wmo_ids'][i])
                    times_allstns.append(raob['times'][i])

    return P_allstns, T_allstns, Td_allstns, U_allstns, V_allstns, wmo_ids_allstns, times_allstns


def commit_sonde(raob):
    P, T, Td, U, V, wmo_ids, times = RemNaN_and_Interp(raob)

    for i,stn in enumerate(wmo_ids):
        radiosonde = Radiosonde.objects.filter(wmo_id=stn).first()
        station = Station.objects.filter(stn_wmoid=stn).first() 

        if station:
            # breakpoint()
            if radiosonde:
                radiosonde.sonde_validtime = times[i]
                radiosonde.temperatureK = T[i]
                radiosonde.dewpointK = Td[i]
                radiosonde.pressurehPA = P[i]
                radiosonde.u_windMS = U[i]
                radiosonde.v_windMS = V[i]
                radiosonde.save()
            else:
                radiosonde = Radiosonde(sonde_validtime=times[i], wmo_id=stn, station_name=station.stn_name,
                                        lat=station.stn_lat, lon=station.stn_lon, temperatureK=T[i], dewpointK=Td[i],
                                        pressurehPA=P[i], u_windMS=U[i], v_windMS=V[i])
                radiosonde.save()
        else:
            print("WMO station {} does not appear to be in the database, skipping.".format(stn))



def extract_madis_data(ftp, file):
    print("Reading {}...".format(file))
    print("\n\n############################\n")
    flo = BytesIO()
    ftp.retrbinary('RETR {}'.format(file), flo.write)
    flo.seek(0)
    with gzip.open(flo, 'rb') as f:
        nc = Dataset('inmemory.nc', memory=f.read())
        Tman = nc.variables['tpMan'][:].filled(fill_value=np.nan)
        DPDman = nc.variables['tdMan'][:].filled(fill_value=np.nan)
        wmo_ids = nc.variables['wmoStaNum'][:].filled(fill_value=np.nan)
        DPDsig = nc.variables['tdSigT'][:].filled(fill_value=np.nan)
        Tsig = nc.variables['tpSigT'][:].filled(fill_value=np.nan)
        synTimes = nc.variables['synTime'][:].filled(fill_value=np.nan)
        raob = {
            "Tsig": nc.variables['tpSigT'][:].filled(fill_value=np.nan),
            "Tdsig": Tsig - DPDsig,
            "Tman": Tman,
            "Psig": nc.variables['prSigT'][:].filled(fill_value=np.nan),
            "Pman": nc.variables['prMan'][:].filled(fill_value=np.nan),
            "Tdman": Tman - DPDman,
            "Wspeed": nc.variables['wsMan'][:].filled(fill_value=np.nan),
            "Wdir": nc.variables['wdMan'][:].filled(fill_value=np.nan),
            "times": [datetime.utcfromtimestamp(tim).replace(tzinfo=pytz.utc) for tim in synTimes],
            "wmo_ids": [str(id).zfill(5) for id in wmo_ids]
        }
        commit_sonde(raob)


def read_madis():
    # Access the MADIS server and login
    ftp = FTP('madis-data.ncep.noaa.gov')
    print(ftp.login())
    print(ftp.cwd('point/raob/netcdf/'))

    # Iterate through the files, find what's been modified since the last call and extract the new data
    for file in ftp.nlst():
        file_timestamp = datetime.strptime(ftp.voidcmd("MDTM {}".format(file))[4:].strip(), '%Y%m%d%H%M%S').replace(microsecond=0).replace(tzinfo=pytz.utc)
        record = UpdateRecord.objects.filter(filename=file).first()
        if record:
            if (file_timestamp != record.updatetime and (timezone.now() - file_timestamp).total_seconds() < 173000):
                print("{} will be updated. Old mod time was {}. New mod time is {}".format(file, record.updatetime, file_timestamp))
                extract_madis_data(ftp, file)
                # breakpoint()
                record.updatetime = file_timestamp
                record.save()
        else:
            if (timezone.now() - file_timestamp).total_seconds() < 173000:
                print("{} has not been downloaded before. Downloading..".format(file))
                extract_madis_data(ftp, file)
                new_record = UpdateRecord(updatetime=file_timestamp, filename=file)
                print("Contents of {} recorded with timestamp {}".format(file, file_timestamp))
                new_record.save()



def run():
    # UpdateRecord.delete_expired(10)
    raob = read_madis()





