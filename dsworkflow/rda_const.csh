#!/bin/csh
#################################################################
# Csh Script to retrieve 14 online Data files of 'ds633.0',
# total 41.53M. This script uses 'wget' to download data.
#
# Highlight this script by Select All, Copy and Paste it into a file;
# make the file executable and run it on command line.
#
# You need pass in your password as a parameter to execute
# this script; or you can set an environment variable RDAPSWD
# if your Operating System supports it.
#
# Contact davestep@ucar.edu (Dave Stepaniak) for further assistance.
#################################################################


set pswd = q9WuTKHd
if(x$pswd == x && `env | grep RDAPSWD` != '') then
 set pswd = $RDAPSWD
endif
if(x$pswd == x) then
 echo
 echo Usage: $0 YourPassword
 echo
 exit 1
endif
set v = `wget -V |grep 'GNU Wget ' | cut -d ' ' -f 3`
set a = `echo $v | cut -d '.' -f 1`
set b = `echo $v | cut -d '.' -f 2`
if(100 * $a + $b > 109) then
 set opt = 'wget --no-check-certificate'
else
 set opt = 'wget'
endif
set opt1 = '-O Authentication.log --save-cookies auth.rda_ucar_edu --post-data'
set opt2 = "email=cwaigl@alaska.edu&passwd=$pswd&action=login"
$opt $opt1="$opt2" https://rda.ucar.edu/cgi-bin/login
if ( $status == 6 ) then
 echo 'Please check that your password is correct.'
 echo "Usage: $0 YourPassword"
 exit 1
endif
set opt1 = "-N --load-cookies auth.rda_ucar_edu"
set opt2 = "$opt $opt1 https://rda.ucar.edu/data/ds633.0/"
set filelist = ( \
  e5.oper.invariant/197901/e5.oper.invariant.128_026_cl.ll025sc.1979010100_1979010100.grb \
  e5.oper.invariant/197901/e5.oper.invariant.128_027_cvl.ll025sc.1979010100_1979010100.grb \
  e5.oper.invariant/197901/e5.oper.invariant.128_028_cvh.ll025sc.1979010100_1979010100.grb \
  e5.oper.invariant/197901/e5.oper.invariant.128_029_tvl.ll025sc.1979010100_1979010100.grb \
  e5.oper.invariant/197901/e5.oper.invariant.128_030_tvh.ll025sc.1979010100_1979010100.grb \
  e5.oper.invariant/197901/e5.oper.invariant.128_043_slt.ll025sc.1979010100_1979010100.grb \
  e5.oper.invariant/197901/e5.oper.invariant.128_074_sdfor.ll025sc.1979010100_1979010100.grb \
  e5.oper.invariant/197901/e5.oper.invariant.128_129_z.ll025sc.1979010100_1979010100.grb \
  e5.oper.invariant/197901/e5.oper.invariant.128_160_sdor.ll025sc.1979010100_1979010100.grb \
  e5.oper.invariant/197901/e5.oper.invariant.128_161_isor.ll025sc.1979010100_1979010100.grb \
  e5.oper.invariant/197901/e5.oper.invariant.128_162_anor.ll025sc.1979010100_1979010100.grb \
  e5.oper.invariant/197901/e5.oper.invariant.128_163_slor.ll025sc.1979010100_1979010100.grb \
  e5.oper.invariant/197901/e5.oper.invariant.128_172_lsm.ll025sc.1979010100_1979010100.grb \
  e5.oper.invariant/197901/e5.oper.invariant.228_007_dl.ll025sc.1979010100_1979010100.grb \
)
while($#filelist > 0)
 set syscmd = "$opt2$filelist[1]"
 echo "$syscmd ..."
 $syscmd
 shift filelist
end

