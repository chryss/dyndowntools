#! /bin/csh -f
#
# c-shell script to download selected files from <server_name> using curl
# NOTE: if you want to run under a different shell, make sure you change
#       the 'set' commands according to your shell's syntax
# after you save the file, don't forget to make it executable
#   i.e. - "chmod 755 <name_of_script>"
#
# you can add cURL options here (progress bars, etc.)
set opts = ""
#
# Replace "xxxxxx" with your rda.ucar.edu password on the next uncommented line
# IMPORTANT NOTE:  If your password uses a special character that has special meaning
#                  to csh, you should escape it with a backslash
#                  Example:  set passwd = "my\!password"
set passwd = 'Gerund10'
set num_chars = `echo "$passwd" |awk '{print length($0)}'`
@ num = 1
set newpass = ""
while ($num <= $num_chars)
  set c = `echo "$passwd" |cut -b{$num}-{$num}`
  if ("$c" == "&") then
    set c = "%26";
  else
    if ("$c" == "?") then
      set c = "%3F"
    else
      if ("$c" == "=") then
        set c = "%3D"
      endif
    endif
  endif
  set newpass = "$newpass$c"
  @ num ++
end
set passwd = "$newpass"
#
if ("$passwd" == "xxxxxx") then
  echo "You need to set your password before you can continue"
  echo "  see the documentation in the script"
  exit
endif
#
# authenticate - NOTE: You should only execute this command ONE TIME.
# Executing this command for every data file you download may cause
# your download privileges to be suspended.
curl -o auth_status.rda.ucar.edu -k -s -c auth.rda.ucar.edu.$$ -d "email=cwaigl@alaska.edu&passwd=$passwd&action=login" https://rda.ucar.edu/cgi-bin/login
#
# download the file(s)
# NOTE:  if you get 403 Forbidden errors when downloading the data files, check
#        the contents of the file 'auth_status.rda.ucar.edu'
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_031_ci.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_031_ci.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_032_asn.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_032_asn.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_033_rsn.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_033_rsn.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_034_sstk.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_034_sstk.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_039_swvl1.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_039_swvl1.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_040_swvl2.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_040_swvl2.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_041_swvl3.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_041_swvl3.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_042_swvl4.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_042_swvl4.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_134_sp.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_134_sp.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_139_stl1.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_139_stl1.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_141_sd.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_141_sd.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_151_msl.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_151_msl.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_165_10u.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_165_10u.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_166_10v.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_166_10v.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_167_2t.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_167_2t.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_168_2d.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_168_2d.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_170_stl2.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_170_stl2.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_183_stl3.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_183_stl3.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_235_skt.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_235_skt.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202106/e5.oper.an.sfc.128_236_stl4.ll025sc.2021060100_2021063023.grb -o e5.oper.an.sfc.128_236_stl4.ll025sc.2021060100_2021063023.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_031_ci.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_031_ci.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_032_asn.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_032_asn.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_033_rsn.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_033_rsn.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_034_sstk.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_034_sstk.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_039_swvl1.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_039_swvl1.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_040_swvl2.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_040_swvl2.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_041_swvl3.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_041_swvl3.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_042_swvl4.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_042_swvl4.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_134_sp.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_134_sp.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_139_stl1.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_139_stl1.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_141_sd.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_141_sd.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_151_msl.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_151_msl.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_165_10u.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_165_10u.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_166_10v.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_166_10v.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_167_2t.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_167_2t.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_168_2d.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_168_2d.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_170_stl2.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_170_stl2.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_183_stl3.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_183_stl3.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_235_skt.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_235_skt.ll025sc.2021050100_2021053123.grb
curl $opts -k -b auth.rda.ucar.edu.$$ https://rda.ucar.edu/data/ds633.0/e5.oper.an.sfc/202105/e5.oper.an.sfc.128_236_stl4.ll025sc.2021050100_2021053123.grb -o e5.oper.an.sfc.128_236_stl4.ll025sc.2021050100_2021053123.grb
#
# clean up
rm auth.rda.ucar.edu.$$ auth_status.rda.ucar.edu
