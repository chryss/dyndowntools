begin

timz = ispan(0,365,1)
timz@calendar = "noleap"
timz@units = "days since 2018-12-31" ;*******************************

utc_date = cd_calendar(timz,0)
year = tointeger(utc_date(:,0))
month = tointeger(utc_date(:,1))
day = tointeger(utc_date(:,2))

date_str = sprinti("%0.4i",year)+"-"+sprinti("%0.2i",month)+"-"+sprinti("%0.2i",day)

c = addfile("auxhist2_d01_"+date_str(0)+"_01:00:00.nc","r")

acsnow = wrf_user_getvar(c,"ACSNOW",-1)

s1 = 23 ; 00z 1/1 *********************

do i = 1,365 ; 1,365 *******************

time = ispan(0,23,1)
time!0 = "Time"
time@long_name = "time" 

a = addfiles(files,"r")
files = systemfunc("ls -1 ./wrfout_d01_"+date_str(i)+"*") + ".nc"
b = addfile("wrfout_d01_"+date_str(i-1)+"_18:00:00.nc","r")

tim = wrf_user_getvar(a,"times",-1)
lat = wrf_user_getvar(a,"lat",-1)
lon = wrf_user_getvar(a,"lon",-1)
it = 0
lats = wrf_user_getvar(a,"XLAT",it)
lons = wrf_user_getvar(a,"XLONG",it)

ntims = dimsizes(tim)
if(ntims.ne.24) then
  print("ntims = "+ntims)
  status_exit(2)
end if

slp = wrf_user_getvar(a,"slp",-1)
slp_a = new((/1,250,320/),"float")
slp_a(0,:,:) = dim_avg_n_Wrap(slp,0)
psfc = wrf_user_getvar(a,"PSFC",-1)
psfc_a = new((/1,250,320/),"float")
psfc_a(0,:,:) = dim_avg_n_Wrap(psfc,0)
uv10 = wrf_user_getvar(a,"uvmet10",-1)
u10 = uv10(0,:,:,:)
u10_a = new((/1,250,320/),"float")
u10_a(0,:,:) = dim_avg_n_Wrap(u10,0)
v10 = uv10(1,:,:,:)
v10_a = new((/1,250,320/),"float")
v10_a(0,:,:) = dim_avg_n_Wrap(v10,0)
t2 = wrf_user_getvar(a,"T2",-1)
t2_a = new((/1,250,320/),"float")
t2_a(0,:,:) = dim_avg_n_Wrap(t2,0)
tmax_a = new((/1,250,320/),"float")
tmax_a(0,:,:) = dim_max_n_Wrap(t2,0)
tmin_a = new((/1,250,320/),"float")
tmin_a(0,:,:) = dim_min_n_Wrap(t2,0)
q2 = wrf_user_getvar(a,"Q2",-1)
q2_a = new((/1,250,320/),"float")
q2_a(0,:,:) = dim_avg_n_Wrap(q2,0)
tsk = wrf_user_getvar(a,"TSK",-1)
tsk_a = new((/1,250,320/),"float")
tsk_a(0,:,:) = dim_avg_n_Wrap(tsk,0)
swe = wrf_user_getvar(a,"SNOW",-1)
swe_a = new((/1,250,320/),"float")
swe_a(0,:,:) = dim_avg_n_Wrap(swe,0)
snow = wrf_user_getvar(a,"SNOWH",-1)
snow_a = new((/1,250,320/),"float")
snow_a(0,:,:) = dim_avg_n_Wrap(snow,0)
snowc = wrf_user_getvar(a,"SNOWC",-1)
snowc_a = new((/1,250,320/),"float")
snowc_a(0,:,:) = dim_avg_n_Wrap(snowc,0)
pw = wrf_user_getvar(a,"pw",-1)
pw_a = new((/1,250,320/),"float")
pw_a(0,:,:) = dim_avg_n_Wrap(pw,0)
rainnc = wrf_user_getvar(a,"RAINNC",-1)
rainbc = wrf_user_getvar(b,"RAINNC",-1)
lh = wrf_user_getvar(a,"LH",-1)
lh_a = new((/1,250,320/),"float")
lh_a(0,:,:) = dim_avg_n_Wrap(lh,0)
sh = wrf_user_getvar(a,"HFX",-1)
sh_a = new((/1,250,320/),"float")
sh_a(0,:,:) = dim_avg_n_Wrap(sh,0)
albedo = wrf_user_getvar(a,"ALBEDO",-1)
albedo_a = new((/1,250,320/),"float")
albedo_a(0,:,:) = dim_avg_n_Wrap(albedo,0)
lwd = wrf_user_getvar(a,"LWDNB",-1)
lwd_a = new((/1,250,320/),"float")
lwd_a(0,:,:) = dim_avg_n_Wrap(lwd,0)
lwdc = wrf_user_getvar(a,"LWDNBC",-1)
lwdc_a = new((/1,250,320/),"float")
lwdc_a(0,:,:) = dim_avg_n_Wrap(lwdc,0)
lwu = wrf_user_getvar(a,"LWUPB",-1)
lwu_a = new((/1,250,320/),"float")
lwu_a(0,:,:) = dim_avg_n_Wrap(lwu,0)
lwuc = wrf_user_getvar(a,"LWUPBC",-1)
lwuc_a = new((/1,250,320/),"float")
lwuc_a(0,:,:) = dim_avg_n_Wrap(lwuc,0)
swd = wrf_user_getvar(a,"SWDNB",-1)
swd_a = new((/1,250,320/),"float")
swd_a(0,:,:) = dim_avg_n_Wrap(swd,0)
swdc = wrf_user_getvar(a,"SWDNBC",-1)
swdc_a = new((/1,250,320/),"float")
swdc_a(0,:,:) = dim_avg_n_Wrap(swdc,0)
swu = wrf_user_getvar(a,"SWUPB",-1)
swu_a = new((/1,250,320/),"float")
swu_a(0,:,:) = dim_avg_n_Wrap(swu,0)
swuc = wrf_user_getvar(a,"SWUPBC",-1)
swuc_a = new((/1,250,320/),"float")
swuc_a(0,:,:) = dim_avg_n_Wrap(swuc,0)

temp = wrf_user_getvar(a,"tc",-1)
q = wrf_user_getvar(a,"QVAPOR",-1)
uvmet = wrf_user_getvar(a,"uvmet",-1)
u = uvmet(0,:,:,:,:)
v = uvmet(1,:,:,:,:)
hgt = wrf_user_getvar(a,"z",-1)
cldfra = wrf_user_getvar(a,"CLDFRA",-1)
p = wrf_user_getvar(a,"pressure",-1)

swat = wrf_user_getvar(a,"SH2O",-1)
swat_a = new((/1,4,250,320/),"float")
swat_a(0,:,:,:) = dim_avg_n_Wrap(swat,0)
smois = wrf_user_getvar(a,"SMOIS",-1)
smois_a = new((/1,4,250,320/),"float")
smois_a(0,:,:,:) = dim_avg_n_Wrap(smois,0)
stemp = wrf_user_getvar(a,"TSLB",-1)
stemp_a = new((/1,4,250,320/),"float")
stemp_a(0,:,:,:) = dim_avg_n_Wrap(stemp,0)

delete([/uv10,uvmet/])

interp_levels = (/100.,200.,300.,400.,500.,700.,850.,925.,1000./)
interp_levels = (/200.,300.,500.,700.,850.,925.,1000./)  ; new levels cw 2022-06-10

opts = True
opts@extrapolate = True
opts@logP = False

tc_plane = wrf_user_vert_interp(a,temp,"pressure",interp_levels,opts)
tc_plane_a = new((/1,9,250,320/),"float")
tc_plane_a(0,:,:,:) = dim_avg_n_Wrap(tc_plane,0)
u_plane  = wrf_user_vert_interp(a,u,"pressure",interp_levels,opts)
u_plane_a = new((/1,9,250,320/),"float")
u_plane_a(0,:,:,:) = dim_avg_n_Wrap(u_plane,0)
v_plane  = wrf_user_vert_interp(a,v,"pressure",interp_levels,opts)
v_plane_a = new((/1,9,250,320/),"float")
v_plane_a(0,:,:,:) = dim_avg_n_Wrap(v_plane,0)
q_plane  = wrf_user_vert_interp(a,q,"pressure",interp_levels,opts)
q_plane_a = new((/1,9,250,320/),"float")
q_plane_a(0,:,:,:) = dim_avg_n_Wrap(q_plane,0)
cldfra_plane = wrf_user_vert_interp(a,cldfra,"pressure",interp_levels,opts)
cldfra_plane_a = new((/1,9,250,320/),"float")
cldfra_plane_a(0,:,:,:) = dim_avg_n_Wrap(cldfra_plane,0)

opts@field_type = "ght"
z_plane  = wrf_user_vert_interp(a,hgt,"pressure",interp_levels,opts)
z_plane_a = new((/1,9,250,320/),"float")
z_plane_a(0,:,:,:) = dim_avg_n_Wrap(z_plane,0)

pcpnc = rainnc
pcpnc(0,:,:) = rainnc(0,:,:)-rainbc(5,:,:)

asnow = acsnow(s1:s1+23,:,:)
asnow(0,:,:) = acsnow(s1,:,:)-acsnow(s1-1,:,:)

ntime = dimsizes(tim)

do t = 1, ntime-1
pcpnc(t,:,:) = rainnc(t,:,:)-rainnc(t-1,:,:)
asnow(t,:,:) = acsnow(s1+1,:,:)-acsnow(s1,:,:)
s1 = s1+1
end do

pcpnc_s = new((/1,250,320/),"float")
pcpnc_s(0,:,:) = dim_sum_n_Wrap(pcpnc,0)
asnow_s = new((/1,250,320/),"float")
asnow_s(0,:,:) = dim_sum_n_Wrap(asnow,0)

delete([/a,b,files,temp,u,v,q,cldfra,hgt/])

tout = str_get_cols(tim(0),0,9)
print(tout)

time@units = "hours since "+tout+" 00:00:00.0"

filout = "/import/SNAP/rtladerjr/4km/cfsr/wrf/hourly/"+year(1)+"/WRFDS_"+tout+".nc"

system(" /bin/rm -f "+filout)
ncdf = addfile(filout,"c")

setfileoption("nc","Format","NetCDF4")
setfileoption("nc","CompressionLevel",5)

filedimdef(ncdf,"Time",-1,True)

globalAtt = True
globalAtt@date    = systemfunc("date")
globalAtt@format  = "version 2"
globalAtt@data    = "Downscaled CFSR"
globalAtt@info    = "Alaska CASC"
globalAtt@contact = "rtladerjr@alaska.edu"
fileattdef(ncdf,globalAtt)

ncdf->time = time
ncdf->lat = lat(0,:,:)
ncdf->lon = lon(0,:,:)
ncdf->XLAT = lats
ncdf->XLONG = lons

ncdf->SLP = slp
ncdf->PSFC = psfc
ncdf->U10 = u10
ncdf->V10 = v10
ncdf->T2 = t2
ncdf->Q2 = q2
ncdf->TSK = tsk
ncdf->SNOW = swe
ncdf->SNOWH = snow
ncdf->SNOWC = snowc
ncdf->PW = pw
ncdf->PCPT = pcpnc
ncdf->ACSNOW = asnow
ncdf->LH = lh
ncdf->HFX = sh
ncdf->ALBEDO = albedo
ncdf->LWDNB = lwd
ncdf->LWDNBC = lwdc
ncdf->LWUPB = lwu
ncdf->LWUPBC = lwuc
ncdf->SWDNB = swd
ncdf->SWDNBC = swdc
ncdf->SWUPB = swu
ncdf->SWUPBC = swuc

ncdf->T = tc_plane
ncdf->U = u_plane
ncdf->V = v_plane
ncdf->QVAPOR = q_plane
ncdf->CLDFRA = cldfra_plane
ncdf->GHT = z_plane

ncdf->SH2O = swat
ncdf->SMOIS = smois
ncdf->TSLB = stemp

;********

dime = ispan(0,0,1)
dime!0 = "Time"
dime@long_name = "time"
dime@units = "days since "+tout+" 00:00:00.0"

slp_a!0 = "Time"
slp_a&Time = dime

psfc_a!0 = "Time"
psfc_a&Time = dime

u10_a!0 = "Time"
u10_a&Time = dime

v10_a!0 = "Time"
v10_a&Time = dime

t2_a!0 = "Time"
t2_a&Time = dime

tmax_a!0 = "Time"
tmax_a&Time = dime

tmin_a!0 = "Time"
tmin_a&Time = dime

q2_a!0 = "Time"
q2_a&Time = dime

tsk_a!0 = "Time"
tsk_a&Time = dime

swe_a!0 = "Time"
swe_a&Time = dime

snow_a!0 = "Time"
snow_a&Time = dime

snowc_a!0 = "Time"
snowc_a&Time = dime

pw_a!0 = "Time"
pw_a&Time = dime

pcpnc_s!0 = "Time"
pcpnc_s&Time = dime

asnow_s!0 = "Time"
asnow_s&Time = dime

lh_a!0 = "Time"
lh_a&Time = dime

sh_a!0 = "Time"
sh_a&Time = dime

albedo_a!0 = "Time"
albedo_a&Time = dime

lwd_a!0 = "Time"
lwd_a&Time = dime

lwdc_a!0 = "Time"
lwdc_a&Time = dime

lwu_a!0 = "Time"
lwu_a&Time = dime

lwuc_a!0 = "Time"
lwuc_a&Time = dime

swd_a!0 = "Time"
swd_a&Time = dime

swdc_a!0 = "Time"
swdc_a&Time = dime

swu_a!0 = "Time"
swu_a&Time = dime

swuc_a!0 = "Time"
swuc_a&Time = dime

tc_plane_a!0 = "Time"
tc_plane_a&Time = dime

u_plane_a!0 = "Time"
u_plane_a&Time = dime

v_plane_a!0 = "Time"
v_plane_a&Time = dime

q_plane_a!0 = "Time"
q_plane_a&Time = dime

cldfra_plane_a!0 = "Time"
cldfra_plane_a&Time = dime

z_plane_a!0 = "Time"
z_plane_a&Time = dime

swat_a!0 = "Time"
swat_a&Time = dime

smois_a!0 = "Time"
smois_a&Time = dime

stemp_a!0 = "Time"
stemp_a&Time = dime

dilout = "/import/SNAP/rtladerjr/4km/cfsr/wrf/daily/"+year(1)+"/WRFDS_"+tout+".nc"

system(" /bin/rm -f "+dilout)
dcdf = addfile(dilout,"c")

setfileoption("nc","Format","NetCDF4")
setfileoption("nc","CompressionLevel",5)

filedimdef(dcdf,"Time",-1,True)

dlobalAtt = True
dlobalAtt@date    = systemfunc("date")
dlobalAtt@format  = "version 2"
dlobalAtt@data    = "Downscaled CFSR"
dlobalAtt@info    = "Alaska CASC"
dlobalAtt@contact = "rtladerjr@alaska.edu"
fileattdef(dcdf,dlobalAtt)

;dcdf->time = dime
dcdf->lat = lat(0,:,:)
dcdf->lon = lon(0,:,:)
dcdf->XLAT = lats
dcdf->XLONG = lons

dcdf->SLP = slp_a
dcdf->PSFC = psfc_a
dcdf->U10 = u10_a
dcdf->V10 = v10_a
dcdf->T2 = t2_a
dcdf->TMAX = tmax_a
dcdf->TMIN = tmin_a
dcdf->Q2 = q2_a
dcdf->TSK = tsk_a
dcdf->SNOW = swe_a
dcdf->SNOWH = snow_a
dcdf->SNOWC = snowc_a
dcdf->PW = pw_a
dcdf->PCPT = pcpnc_s
dcdf->ACSNOW = asnow_s
dcdf->LH = lh_a
dcdf->HFX = sh_a
dcdf->ALBEDO = albedo_a
dcdf->LWDNB = lwd_a
dcdf->LWDNBC = lwdc_a
dcdf->LWUPB = lwu_a
dcdf->LWUPBC = lwuc_a
dcdf->SWDNB = swd_a
dcdf->SWDNBC = swdc_a
dcdf->SWUPB = swu_a
dcdf->SWUPBC = swuc_a

dcdf->T = tc_plane_a
dcdf->U = u_plane_a
dcdf->V = v_plane_a
dcdf->QVAPOR = q_plane_a
dcdf->CLDFRA = cldfra_plane_a
dcdf->GHT = z_plane_a

dcdf->SH2O = swat_a
dcdf->SMOIS = smois_a
dcdf->TSLB = stemp_a

;********
s1 = s1+1

delete([/time,tim,lat,lon,ntims,slp,psfc,u10,v10,t2,q2,tsk,swe,snow,snowc,pw,rainnc,rainbc,lh/])
delete([/sh,albedo,lwd,lwdc,lwu,lwuc,swd,swdc,swu,swuc,p,swat,smois,stemp,interp_levels,opts/])
delete([/tc_plane,u_plane,v_plane,q_plane,cldfra_plane,z_plane,pcpnc,asnow,ntime,tout,filout/])
delete([/lats,lons,dime,dilout,globalAtt,dlobalAtt/])
delete([/slp_a,psfc_a,u10_a,v10_a,t2_a,tmax_a,tmin_a,q2_a,tsk_a,swe_a,snow_a,snowc_a,pw_a/])
delete([/pcpnc_s,asnow_s,lh_a,sh_a,albedo_a,lwd_a,lwdc_a,lwu_a,lwuc_a,swd_a,swdc_a,swu_a,swuc_a/])
delete([/tc_plane_a,u_plane_a,v_plane_a,q_plane_a,cldfra_plane_a,z_plane_a,swat_a,smois_a,stemp_a/])

end do

print("s1 = "+s1)
end
