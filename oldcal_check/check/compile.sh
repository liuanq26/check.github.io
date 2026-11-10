#rm -f a.out
#g++ -Wall -g check.cpp `root-config --cflags` `root-config --libs` -lRooFitCore -lRooFit -L/cvmfs/bes3.ihep.ac.cn/bes3sw/ExternalLib/lcg/LCG_84/tbb/42_20140122/x86_64-centos7-gcc49-opt/lib/ -ltbb


#pdf try
read -p "Generate PDF version? (y/n): " answer

rm -f a.out
if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
g++ -Wall -g check_pdf.cpp `root-config --cflags` `root-config --libs` -lRooFitCore -lRooFit -L/cvmfs/bes3.ihep.ac.cn/bes3sw/ExternalLib/lcg/LCG_84/tbb/42_20140122/x86_64-centos7-gcc49-opt/lib/ -ltbb
else
g++ -Wall -g check.cpp `root-config --cflags` `root-config --libs` -lRooFitCore -lRooFit -L/cvmfs/bes3.ihep.ac.cn/bes3sw/ExternalLib/lcg/LCG_84/tbb/42_20140122/x86_64-centos7-gcc49-opt/lib/ -ltbb
fi

echo "Compilation ok"


