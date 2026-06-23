begin


;read in all of the variables that will be needed

datin="/import/SNAP/cwaigl/wrf_era5/221202/"
;print(datin)

files = systemfunc("ls -1 "+datin+"/wrfout_d02_*") + ".nc"
a = addfiles(files,"r")


;*********other coordinate fields**********

tim = wrf_user_getvar(a,"times",-1)  ; times
lat = wrf_user_getvar(a,"lat",-1)  ; lat
lon = wrf_user_getvar(a,"lon",-1)  ; lon

ntims = dimsizes(tim)
print(ntims)
;if (ntims .ne. 54) then
;status_exit(2)
;end if

;**********surface fields***********

dbz = wrf_user_getvar(a,"mdbz",-1)  ; radar dbz estimate
ctt = wrf_user_getvar(a,"ctt",-1)  ; cloud top temperature estimate

slp = wrf_user_getvar(a,"slp",-1)  ; slp
psfc = wrf_user_getvar(a,"PSFC",-1)  ; surface pressure

uv10 = wrf_user_getvar(a,"uvmet10",-1)  ; 10m earth-relative winds
t2 = wrf_user_getvar(a,"T2",-1)  ; 2m temperature
q2 = wrf_user_getvar(a,"Q2",-1)  ; specific humidity
rainc = wrf_user_getvar(a,"RAINC",-1)  ; convective precipitation
rainnc = wrf_user_getvar(a,"RAINNC",-1)  ; non-convective precipitation
acsnow = wrf_user_getvar(a,"ACSNOW",-1)  ; snow fall
lh = wrf_user_getvar(a,"LH",-1)  ; latent heat flux
sh = wrf_user_getvar(a,"HFX",-1)  ; sensible heat flux
seaice = wrf_user_getvar(a,"SEAICE",-1)  ; sea ice concentration
albedo = wrf_user_getvar(a,"ALBEDO",-1)  ; sea ice concentration

tsk = wrf_user_getvar(a,"TSK",-1)  ; skin temperature

swe = wrf_user_getvar(a,"SNOW",-1)  ; snow water equivalent
snow = wrf_user_getvar(a,"SNOWH",-1)  ; snow depth
snowc = wrf_user_getvar(a,"SNOWC",-1)  ; snow cover

lwd = wrf_user_getvar(a,"LWDNB",-1)  ; downward longwave
lwdc = wrf_user_getvar(a,"LWDNBC",-1)  ; downward longwave without clouds
lwu = wrf_user_getvar(a,"LWUPB",-1)  ; upward longwave
lwuc = wrf_user_getvar(a,"LWUPBC",-1)  ; upward longwave without clouds
swd = wrf_user_getvar(a,"SWDNB",-1)  ; downward shortwave
swdc = wrf_user_getvar(a,"SWDNBC",-1)  ; downward shortwave without clouds
swu = wrf_user_getvar(a,"SWUPB",-1)  ; upward shortwave
swuc= wrf_user_getvar(a,"SWUPBC",-1)  ; upward shortwave without clouds

;*********soil fields**********

smois = wrf_user_getvar(a,"SMOIS",-1)  ; soil moisture
swat = wrf_user_getvar(a,"SH2O",-1)  ; soil water
;stemp = wrf_user_getvar(a,"TSLB",-1)  ; soil temperature

;*********upper-air fields**********

temp = wrf_user_getvar(a,"tc",-1)  ; temperature
q  = wrf_user_getvar(a,"QVAPOR",-1)  ; specific humidity
uvmet = wrf_user_getvar(a,"uvmet",-1)  ; winds
hgt = wrf_user_getvar(a,"z",-1)  ; height
cldfra = wrf_user_getvar(a,"CLDFRA",-1)  ; cloud fraction
p = wrf_user_getvar(a,"pressure",-1)  ; surface pressure

;*************************************************************************
;****************reorganize and interpolate as needed*********************
;*************************************************************************

;reorganize the wind variables

u = uvmet(0,:,:,:,:)
v = uvmet(1,:,:,:,:)

delete(uvmet)

u10 = uv10(0,:,:,:)
v10 = uv10(1,:,:,:)

delete(uv10)

printVarSummary(p)

;>>>>>>>interpolate the upper-air variables to pressure level<<<<<<<<

; Horizontally interpolate to pressure coordinates ("p")

interp_levels = (/200.,300.,500.,700.,850.,925.,1000./)   ; pressure levels

;tc_plane = wrf_user_intrp3d(temp,p,"h",pressure,0.,False)

opts             = True
opts@extrapolate = True
;  opts@field_type  = "T"
opts@logP        = False

tc_plane = wrf_user_vert_interp(a,temp,"pressure",interp_levels,opts)

print("tc")
u_plane = wrf_user_vert_interp(a,u,"pressure",interp_levels,opts)
print("u")
v_plane = wrf_user_vert_interp(a,v,"pressure",interp_levels,opts)
q_plane = wrf_user_vert_interp(a,q,"pressure",interp_levels,opts)

opts@field_type  = "ght"
z_plane = wrf_user_vert_interp(a,hgt,"pressure",interp_levels,opts)

print("interp done")

delete([/temp,u,v,q,hgt/])

;compute hourly precipitation/snow/heat flux from accumulated numbers

pcpc=rainc
pcpnc=rainnc
asnow=acsnow

ntime = dimsizes(tim)

do t=1,ntime-1
pcpc(t,:,:)=rainc(t,:,:)-rainc(t-1,:,:)
pcpnc(t,:,:)=rainnc(t,:,:)-rainnc(t-1,:,:)
asnow(t,:,:)=acsnow(t,:,:)-acsnow(t-1,:,:)
end do

print("accum done")
;**************************************************************************
;************************cut data && write to file*************************
;**************************************************************************


timz = ispan(0,23,1)
timz!0 = "Time"
timz@long_name = "time"

do d=0,1
s=6+24*d
e=29+24*d

dbzout=dbz(s:e,:,:)
cttout=ctt(s:e,:,:)

slpout=slp(s:e,:,:)
t2out=t2(s:e,:,:)
q2out=q2(s:e,:,:)
tskout=tsk(s:e,:,:)
psfcout=psfc(s:e,:,:)

snowout=snow(s:e,:,:)
sweout=swe(s:e,:,:)
snowcout=snowc(s:e,:,:)
seaiceout=seaice(s:e,:,:)

lwdout=lwd(s:e,:,:)
lwdcout=lwdc(s:e,:,:)
lwuout=lwu(s:e,:,:)
lwucout=lwuc(s:e,:,:)
swdout=swd(s:e,:,:)
swdcout=swdc(s:e,:,:)
swuout=swu(s:e,:,:)
swucout=swuc(s:e,:,:)

u10out=u10(s:e,:,:)
v10out=v10(s:e,:,:)

pcpcout=pcpc(s:e,:,:)
pcpncout=pcpnc(s:e,:,:)

pcptout=pcpcout
pcptout@description = "Total accumulated precipitation = convective + non-convective"
pcptout=pcpcout+pcpncout

albedoout=albedo(s:e,:,:)
asnowout=asnow(s:e,:,:)
lhout=lh(s:e,:,:)
shout=sh(s:e,:,:)

smois_out=smois(s:e,:,:,:)
swat_out=swat(s:e,:,:,:)
;stemp_out=stemp(s:e,:,:,:)

tc_plane_out = tc_plane(s:e,:,:,:)
u_plane_out = u_plane(s:e,:,:,:)
v_plane_out = v_plane(s:e,:,:,:)
q_plane_out = q_plane(s:e,:,:,:)
z_plane_out = z_plane(s:e,:,:,:)

tout=str_get_cols(tim(s),0,9)
print(tout)
timz@units="hours since "+tout+" 00:00:00.0"

filout="wrf_proctest_d02_"+tout+"_chrisw.nc"

setfileoption("nc","Format","NetCDF4")
setfileoption("nc","CompressionLevel",5)

system("/bin/rm -f "+filout)
ncdf = addfile(filout,"c")
filedimdef(ncdf,"Time",-1,True)

globalAtt            = True
globalAtt@date    = systemfunc("date")
globalAtt@format    = "version 2"
globalAtt@data    = "Downscaled ERA-Interim"
globalAtt@info    = "Alaska CSC"
globalAtt@contact    = "pbieniek@alaska.edu"
fileattdef( ncdf, globalAtt )


ncdf->time = timz
ncdf->lat = lat(0,:,:)
ncdf->lon = lon(0,:,:)

ncdf->TSK = tskout
ncdf->T2 = t2out
ncdf->Q2 = q2out
ncdf->U10 = u10out
ncdf->V10 = v10out

ncdf->SWUPBC = swucout
ncdf->SWUPB = swuout
ncdf->LWUPBC = lwucout
ncdf->LWUPB = lwuout

ncdf->SWDNBC = swdcout
ncdf->SWDNB = swdout
ncdf->LWDNBC = lwdcout
ncdf->LWDNB = lwdout

ncdf->ALBEDO = albedoout
ncdf->SNOW = sweout
ncdf->SNOWH = snowout
ncdf->SNOWC = snowcout
;ncdf->SEAICE = seaiceout

;ncdf->PCPC = pcpcout
ncdf->PCPNC = pcpncout
;ncdf->PCPT = pcptout
ncdf->ACSNOW = asnowout

ncdf->SLP = slpout
ncdf->PSFC = psfcout
ncdf->HFX = shout
ncdf->LH = lhout

ncdf->U = u_plane_out
ncdf->V = v_plane_out
ncdf->QVAPOR = q_plane_out
ncdf->T = tc_plane_out
ncdf->GHT = z_plane_out

ncdf->SH20 = swat_out
ncdf->SMOIS = smois_out
;ncdf->SH20 = swat_out
;ncdf->TSLB = stemp_out

ncdf->dbz = dbzout
ncdf->ctt = cttout

end do

print("file stuff done")


status_exit(100) ;fake status exit number so I can check that it worked


end
