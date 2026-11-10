#include <iostream>
#include <iomanip>
#include <fstream>
#include <string>
#include <string.h>

#include "TGraph.h"
#include "TGraphErrors.h"
#include "TApplication.h"
#include "TCanvas.h"
#include "TH2F.h"
#include "TH1F.h"
#include "TMarker.h"
#include "TLegend.h"
#include "TLatex.h"
#include "TStyle.h"
#include "TFolder.h"
#include "TF1.h"
#include "TFile.h"
#include "TMath.h"
#include "TROOT.h"
#include "RooFitResult.h"
#include "RooRealVar.h"
#include "RooDataHist.h"
#include "RooCBShape.h"
#include "RooPlot.h"
#include "RooGlobalFunc.h"


const int NFILE = 10000;

using namespace std;

Double_t fitdgaus1(Double_t *x, Double_t *par)
{
     Double_t arg1 = 0;
     arg1 = par[0]*par[1] * ( TMath::Gaus(x[0], par[2], par[3]) )
	  / (sqrt( 2 * (TMath::Pi()) ) * par[3] );
     Double_t arg2 = 0;
     arg2 = par[0]*(1-par[1]) * ( TMath::Gaus(x[0], par[4], par[5]) )
	  / (sqrt( 2 * (TMath::Pi()) ) * par[5] );

     Double_t fitval = arg1 + arg2;
     return fitval;
}

int main(int argc, char* argv[]){
     char path[200];
     //      sprintf(path, "/ihepbatch/besd13/wulh/testDB/");

     double xmin, xmax, xpeak;
     xpeak = 1.83; xmin = 0.9; xmax = 1.95;

     gStyle->SetPadLeftMargin(0.15);
     gStyle->SetPadBottomMargin(0.15);
     gStyle->SetPadRightMargin(0.05);
     gStyle->SetPadTopMargin(0.05);
     gStyle->SetFrameLineWidth(2);
     gStyle->SetFrameLineWidth(2);
     gStyle->SetCanvasColor(10);
     gStyle->SetPadGridY(1);
     // gStyle->SetPadGridX(1);
     gStyle->SetTitleXSize(0.06);
     gStyle->SetTitleXOffset(1);
     gStyle->SetTitleYSize(0.07);
     gStyle->SetTitleYOffset(0.9);
     gStyle->SetTitleFont(42,"xyz");
     gStyle->SetStatFont(42);
     gStyle->SetLabelFont(42,"xyz");
     gStyle->SetLabelSize(0.06,"xyz");
     gStyle->SetLabelOffset(0.01,"xyz");
     gStyle->SetNdivisions(505,"xyz");
     int run;
     int runmin;
     int runmax;
     char fname[200];
     if( argc > 3 ){
	  sscanf(argv[1], "%s", path);
	  sscanf(argv[2], "%d", &runmin);
	  sscanf(argv[3], "%d", &runmax);
     } else{
	  cout << "bad argument" << endl;
	  return -1;
     }
     if(runmin > runmax){
	  cout << "bad argument" << endl;
	  return -1;
     }

   
//     TH2F* h2 = new TH2F("h2", "", 500, runmin-5, runmax+5, 100, 125.0, 155.0);
     //TH2F* h2 = new TH2F("reso", "", 500, runmin-5, runmax+5, 100, 115.0, 155.0);
     TH2F* h2 = new TH2F("reso", "", 500, runmin-5, runmax+5, 100, 100.0, 130.0);
     h2->SetStats(0);

     TH2F* h3 = new TH2F("h3", "", 500, runmin-5, runmax+5, 100, 0.4, 32.0);
     h3->SetStats(0);

     TH2F* h4 = new TH2F("sigmaP", "", 500, runmin-5, runmax+5, 100, 0., 30.0);
     h4->SetStats(0);

     //TH2F* h5 = new TH2F("h5", "", 500, runmin-5, runmax+5, 400, xpeak-0.2, xpeak+0.2);
      //TH2F* h5 = new TH2F("Pmean", "", 500, runmin-5, runmax+5, 400, xmin, xmax);
      //TH2F* h5 = new TH2F("Pmean", "", 500, runmin-5, runmax+5, 400, 1.8, 1.9);
      TH2F* h5 = new TH2F("Pmean", "", 500, runmin-5, runmax+5, 400, 1.82, 2.5);
     h5->SetStats(0);

     TH2F* h6 = new TH2F("h6", "", 500, runmin-5, runmax+5, 100, 0.9, 1);
     h6->SetStats(0);

     TH2F* h7 = new TH2F("h7", "", 500, runmin-5, runmax+5, 100, 0, 1);
     h7->SetStats(0);

     TH2F* h8 = new TH2F("h8", "", 500, runmin-5, runmax+5, 100, 0, 0.5);
     h8->SetStats(0);

//     TH2F* h9 = new TH2F("h9", "", 500, runmin-5, runmax+5, 100, 0.8, 1);
     TH2F* h9 = new TH2F("recEff", "", 500, runmin-5, runmax+5, 100, 0, 1);
     h9->SetStats(0);

     TH2F* h9_2 = new TH2F("hitEff", "", 500, runmin-5, runmax+5, 100, 0.0, 1);
     h9_2->SetStats(0);

     //   TH2F* h10 = new TH2F("h10", "", 500, runmin-5, runmax+5, 50, -1, 1);
     TH2F* h10 = new TH2F("z0", "", 500, runmin-5, runmax+5, 50, -10, 10);
     h10->SetStats(0);

     TH2F* h11 = new TH2F("h11", "", 500, runmin-5, runmax+5, 50, 0.0, 1.5);
     h11->SetStats(0);

     TGraph* grreso = new TGraph();
     grreso->SetMarkerStyle(20);
     grreso->SetMarkerColor(kAzure+2);

     TGraphErrors* grmom = new TGraphErrors();
     grmom->SetMarkerStyle(20);
     grmom->SetMarkerColor(kAzure+2);

     TGraphErrors* grmomcms = new TGraphErrors();
     grmomcms->SetMarkerStyle(20);
     grmomcms->SetMarkerColor(kAzure+2);

     TGraphErrors* grpmean = new TGraphErrors();
     grpmean->SetMarkerStyle(20);
     grpmean->SetMarkerSize(0.8);
     grpmean->SetMarkerColor(kAzure+2);

     TGraphErrors* grppos = new TGraphErrors();
     grppos->SetMarkerStyle(20);
     grppos->SetMarkerSize(0.8);
     grppos->SetMarkerColor(2);
     grppos->SetMarkerColor(kAzure+2);

     TGraphErrors* grpneg = new TGraphErrors();
     grpneg->SetMarkerStyle(20);
     grpneg->SetMarkerSize(0.8);
     grpneg->SetMarkerColor(4);
     grpneg->SetMarkerColor(kRed+1);

     TGraphErrors* greff = new TGraphErrors();
     greff->SetMarkerStyle(20);
     greff->SetMarkerColor(4);

     TGraphErrors* grbbeff = new TGraphErrors();
     grbbeff->SetMarkerStyle(20);
     grbbeff->SetMarkerColor(4);

     TGraphErrors* grcal = new TGraphErrors();
     grcal->SetMarkerStyle(20);
     grcal->SetMarkerColor(4);

     TGraphErrors* grdet1 = new TGraphErrors();
     grdet1->SetMarkerStyle(20);
     grdet1->SetMarkerColor(kAzure+2);

     TGraphErrors* grdet2 = new TGraphErrors();
     grdet2->SetMarkerStyle(20);
     grdet2->SetMarkerColor(kAzure+2);

     TGraphErrors* grdet3 = new TGraphErrors();
     grdet3->SetMarkerStyle(20);
     grdet3->SetMarkerColor(kMagenta-7);

     TGraphErrors* grhit = new TGraphErrors();
     grhit->SetMarkerStyle(20);
     grhit->SetMarkerColor(4);

     TGraphErrors* grz0 = new TGraphErrors();
     grz0->SetMarkerStyle(20);
     grz0->SetMarkerColor(1);
     grz0->SetMarkerColor(kAzure+2);

     TGraphErrors* grz0sig = new TGraphErrors();
     grz0sig->SetMarkerStyle(20);
     grz0sig->SetMarkerColor(1);


     TF1 *dgaus1 = new TF1("dgaus1", fitdgaus1, -1.0, 1.0, 6);
     dgaus1 -> SetParameter(2, 0);
     dgaus1 -> SetParameter(3, 0.04);
     dgaus1 -> SetParameter(4, 0);
     dgaus1 -> SetParameter(5, 0.2);

     bool runwrt[NFILE];
     int runnum[NFILE], runnumRd[NFILE];
     string runFlag[NFILE], runFlagRd[NFILE];
     double reso[NFILE], resoRd[NFILE];
     double rms[NFILE], rmsRd[NFILE];
     double plab[NFILE], plabRd[NFILE];
     double plabErr[NFILE], plabErrRd[NFILE];
     double pcms[NFILE], pcmsRd[NFILE];
     double pcmsErr[NFILE], pcmsErrRd[NFILE];
     double pmean[NFILE], pmeanRd[NFILE];
     double pmeanErr[NFILE], pmeanErrRd[NFILE];
     double ppos[NFILE], pposRd[NFILE];
     double pposErr[NFILE], pposErrRd[NFILE];
     double pneg[NFILE], pnegRd[NFILE];
     double pnegErr[NFILE], pnegErrRd[NFILE];
     double effRec[NFILE], effRecRd[NFILE];
     double effRecErr[NFILE], effRecErrRd[NFILE];
     double bbeffRec[NFILE], bbeffRecRd[NFILE];
     double bbeffRecErr[NFILE], bbeffRecErrRd[NFILE];
     double effCal[NFILE], effCalRd[NFILE];
     double effCalErr[NFILE], effCalErrRd[NFILE];
     double effDet1[NFILE], effDet1Rd[NFILE];
     double effDet1Err[NFILE], effDet1ErrRd[NFILE];
     double effDet2[NFILE], effDet2Rd[NFILE];
     double effDet2Err[NFILE], effDet2ErrRd[NFILE];
     double effDet3[NFILE], effDet3Rd[NFILE];
     double effDet3Err[NFILE], effDet3ErrRd[NFILE];
     double noiseRatio[NFILE], noiseRatioRd[NFILE];
     double noiseRatioErr[NFILE], noiseRatioErrRd[NFILE];
     double z0[NFILE], z0Rd[NFILE];
     double z0err[NFILE], z0errRd[NFILE];
     double z0sig[NFILE], z0sigRd[NFILE];
     double z0sigerr[NFILE], z0sigerrRd[NFILE];

     int k=0;
     ifstream fin("fitResults.txt");
     while(fin >> run){
	  runnumRd[k] = run;
	  // cout << "read fitResults, run = " << run << endl;
	  fin >> runFlagRd[k] >> resoRd[k] >> rmsRd[k] >> plabRd[k] >> plabErrRd[k]
	      >> pcmsRd[k] >> pcmsErrRd[k] >> pmeanRd[k] >> pmeanErrRd[k] >> pposRd[k] >> pposErrRd[k]
	      >> pnegRd[k] >> pnegErrRd[k] >> effRecRd[k] >> effRecErrRd[k] >> bbeffRecRd[k] >> bbeffRecErrRd[k]
	      >> effCalRd[k] >> effCalErrRd[k] >> effDet1Rd[k] >> effDet1ErrRd[k]
	      >> effDet2Rd[k] >> effDet2ErrRd[k] >> effDet3Rd[k] >> effDet3ErrRd[k]
	      >> noiseRatioRd[k] >> noiseRatioErrRd[k] >> z0Rd[k] >> z0errRd[k]
	      >> z0sigRd[k] >> z0sigerrRd[k];

	  k++;
     }
     int nRunExist = k;
     fin.close();

     // RooRealVar x("", "P (GeV/c)", 1.69, 1.78);
     // RooRealVar m1("P", "P", 1.745, 1.69, 1.78); // 47467 ~ 47493
     // RooRealVar x("", "P (GeV/c)", 1.78, 1.88);
     // RooRealVar m1("P", "P", 1.84, 1.78, 1.88); // 47494 ~ 47505
     // RooRealVar x("", "P (GeV/c)", 2.0, 2.15);
     // RooRealVar m1("P", "P", 2.1, 2.0, 2.15); // 47543 ~ 
     // RooRealVar x("", "P (GeV/c)", 2.05, 2.18);
     // RooRealVar m1("P", "P", 2.1, 2.05, 2.18); // 47543 ~ 
     // RooRealVar x("", "P (GeV/c)", 1.77, 1.9);
     // RooRealVar m1("P", "P", 1.82, 1.77, 1.9); // 51499 ~ 
     // RooRealVar x("", "P (GeV/c)", 1.71, 1.81);
     // RooRealVar m1("P", "P", 1.76, 1.71, 1.81); // 51584 ~ 

     // RooRealVar s1("#sigmaP", "S1", 0.0119, 0.005, 0.05);
     // RooRealVar a("#alpha", "a", 1.1, 0, 5);
     // RooRealVar n("n", "n", 1.54, 0, 10);
     // RooCBShape pdf1("pdf1", "PDF1", x, m1, s1, a, n);

     int i=0;

	// double reco_total = 0;

     for(run=runmin; run<=runmax; run++){
	  if(65257==run) continue;
	  if(65747==run) continue;
	  if(70522<=run&&70524>=run) continue;
	  runwrt[i] = false;
	  bool fileExist = false;
// 	if( (run>13988) && (run<14395) ) continue;  // psi'' scan
	  for(k=0; k<nRunExist; k++){
	       if(run == runnumRd[k]){
		    cout << "read run " << run << " from fitResults.txt" << endl;
		    runnum[i] = runnumRd[k];
		    runFlag[i] = runFlagRd[k];
		    reso[i] = resoRd[k];
		    rms[i] = rmsRd[k];
		    plab[i] = plabRd[k];
		    plabErr[i] = plabErrRd[k];
		    pcms[i] = pcmsRd[k];
		    pcmsErr[i] = pcmsErrRd[k];
		    pmean[i] = pmeanRd[k];
		    pmeanErr[i] = pmeanErrRd[k];
		    ppos[i] = pposRd[k];
		    pposErr[i] = pposErrRd[k];
		    pneg[i] = pnegRd[k];
		    pnegErr[i] = pnegErrRd[k];
		    effRec[i] = effRecRd[k];
		    effRecErr[i] = effRecErrRd[k];
		    bbeffRec[i] = bbeffRecRd[k];
		    bbeffRecErr[i] = bbeffRecErrRd[k];
		    effCal[i] = effCalRd[k];
		    effCalErr[i] = effCalErrRd[k];
		    effDet1[i] = effDet1Rd[k];
		    effDet1Err[i] = effDet1ErrRd[k];
		    effDet2[i] = effDet2Rd[k];
		    effDet2Err[i] = effDet2ErrRd[k];
		    effDet3[i] = effDet3Rd[k];
		    effDet3Err[i] = effDet3ErrRd[k];
		    if(effDet1[i]>0.9999) effDet1[i] = effDet1[i-1];
		    if(effDet2[i]>0.99) effDet2[i] = effDet2[i-1];
		    if(effDet3[i]>0.9999) effDet3[i] = effDet3[i-1];
		    noiseRatio[i] = noiseRatioRd[k];
		    noiseRatioErr[i] = noiseRatioErrRd[k];
		    z0[i] = z0Rd[k];
		    z0err[i] = z0errRd[k];
		    z0sig[i] = z0sigRd[k];
		    z0sigerr[i] = z0sigerrRd[k];

	//		reco_total=reco_total+reso[i];
	//		cout<<"================================================"<<reso[i]<<endl;

		    grreso->SetPoint(i, (double)run, reso[i]);
		    // grreso->SetPoint(i, (double)run, rms[i]);
		    // if(rms[i]<120.) grreso->SetPoint(i, (double)run, rms[i]);
		    grmom->SetPoint(i, (double)run, plab[i]);
		    grmom->SetPointError(i, 0, plabErr[i]);
		    grmomcms->SetPoint(i, (double)run, pcms[i]);
		    // if((pcms[i]>10)&&(pcms[i]<22)) grmomcms->SetPoint(i, (double)run, pcms[i]);
		    // else grmomcms->SetPoint(i, (double)run, -999.);
		    grmomcms->SetPointError(i, 0, pcmsErr[i]);
		    grpmean->SetPoint(i, (double)run, pmean[i]);
		    grpmean->SetPointError(i, 0, pmeanErr[i]);
		    grppos->SetPoint(i, (double)run, ppos[i]);
		    grppos->SetPointError(i, 0, pposErr[i]);
		    grpneg->SetPoint(i, (double)run, pneg[i]);
		    grpneg->SetPointError(i, 0, pnegErr[i]);
		    greff->SetPoint(i, (double)run, effRec[i]);
		    greff->SetPointError(i, 0, effRecErr[i]);
		    grbbeff->SetPoint(i, (double)run, bbeffRec[i]);
		    grbbeff->SetPointError(i, 0, bbeffRecErr[i]);
		    grcal->SetPoint(i, (double)run, effCal[i]);
		    grcal->SetPointError(i, 0, effCalErr[i]);
		    grdet1->SetPoint(i, (double)run, effDet1[i]);
		    grdet1->SetPointError(i, 0, effDet1Err[i]);
		    grdet2->SetPoint(i, (double)run, effDet2[i]);
		    grdet2->SetPointError(i, 0, effDet2Err[i]);
		    grdet3->SetPoint(i, (double)run, effDet3[i]);
		    grdet3->SetPointError(i, 0, effDet3Err[i]);
		    grhit->SetPoint(i, (double)run, noiseRatio[i]);
		    grhit->SetPointError(i, 0, noiseRatioErr[i]);
		    grz0->SetPoint(i, (double)run, z0[i]);
		    grz0->SetPointError(i, 0, z0err[i]);
		    grz0sig->SetPoint(i, (double)run, z0sig[i]);
		    grz0sig->SetPointError(i, 0, z0sigerr[i]);

		    i++;
		    fileExist = true;

//                 continue; // this is a bug
		    break;
	       }
	  }
	  if(fileExist) continue;
// 	else {cout << "run fit " << run << endl; continue;}

	  sprintf(fname, "%s/hist%d.root", path, run);
	  cout << "read file " << fname << endl;
	  runnum[i] = run;

	  TFile f(fname);
	  if(!f.IsOpen()) continue;
	  runwrt[i] = true;
	  TFolder* fdcom = (TFolder*)f.Get("common");

	  TH1F* htes = (TH1F*)( fdcom->FindObjectAny("TesAll"));
	  int nTes = (int)htes->GetEntries();
	  if(nTes < 200) continue;

	  //           TH1F* h1 = (TH1F*)( fdcom->FindObjectAny("HResAllExc"));
	  TH1F* h1 = (TH1F*)( fdcom->FindObjectAny("HResAllAve"));

	  double entry =  h1->GetEntries();
	  double vini = entry * 0.01 * 0.8;
	   dgaus1 -> SetParameter(0, vini);
	  // dgaus1 -> SetParameter(1, 0.7);
	  dgaus1 -> SetParameter(2, 0);
	  dgaus1 -> SetParameter(3, 0.04);
	  dgaus1 -> SetParameter(4, 0);
	  dgaus1 -> SetParameter(5, 0.12);
	  h1->Fit("dgaus1", "Q");
	  //           double chisq = dgaus1 -> GetChisquare();
	  //           double cons1 = dgaus1 -> GetParameter(0);
	  //           double mean1 = dgaus1 -> GetParameter(2);
	  //           double mean2 = dgaus1 -> GetParameter(4);
	  double prop = dgaus1 -> GetParameter(1);
	  double sigm1 = dgaus1 -> GetParameter(3);
	  double sigm2 = dgaus1 -> GetParameter(5);
	  reso[i] = sqrt( sigm1*sigm1*prop + sigm2*sigm2*(1-prop) ) * 1000.0;
	  rms[i] = (h1->GetRMS())*1000.0;

	  cout<<"reso"<<i<<"\t"<<reso[i]<<endl;
	  // grreso->SetPoint(i, (double)run, reso[i]);
	  grreso->SetPoint(i, (double)run, rms[i]);
	  // if(rms[i]<120.) grreso->SetPoint(i, (double)run, rms[i]);

	  double xminFit = 0.;
	  double xmaxFit = 0.;
	  if(run<=85383){
	       xpeak = 0.94; xmin = 0.885; xmax = 0.96;
	       xminFit = 0.925; xmaxFit = 0.95;
	  } else if(run<=90616){
	       xpeak = 1.843; xmin = 1.75; xmax = 1.9;
	       xminFit = 1.79; xmaxFit = 1.88;
	  } else if(run<=1000000){
	       xpeak = 2.35; xmin = 2.22; xmax = 2.44;
	       xminFit = 2.26; xmaxFit = 2.4;
	  }

	  RooRealVar x("x", "P (GeV/c)", xmin, xmax);
	  RooRealVar m1("P", "P", xpeak, xmin, xmax);
	  RooRealVar s1("#sigmaP", "S1", 0.005, 0.003, 0.05);
	  RooRealVar a("#alpha", "a", 1.0, 0, 5);
	  RooRealVar n("n", "n", 1.54, 0, 10);

	  TH1F* hpCms = (TH1F*)( fdcom->FindObjectAny("HPCMS"));
	  // double momMean = hpCms->GetMean();
	  // m1.setRange(momMean-0.15, momMean+0.1);
	  // m1.setVal(momMean);
	  RooCBShape pdf_pcms("pdf_pcms", "PDF_pcms", x, m1, s1, a, n);
	  RooDataHist data_pcms("HP", "dataset with x", x, hpCms);
	  pdf_pcms.fitTo(data_pcms, RooFit::PrintLevel(-1), RooFit::Range(xminFit, xmaxFit));
	  pmean[i] = m1.getVal();
	  pmeanErr[i] = m1.getError();
	  pcms[i] = (s1.getVal())*1000.0;
	  pcmsErr[i] = (s1.getError())*1000.0;
	  // if((pcms[i]>10)&&(pcms[i]<22)) grmomcms->SetPoint(i, (double)run, pcms[i]);
	  // else grmomcms->SetPoint(i, (double)run, -999.);
	  grmomcms->SetPoint(i, (double)run, pcms[i]);
	  grmomcms->SetPointError(i, 0, pcmsErr[i]);
	  grpmean->SetPoint(i, (double)run, pmean[i]);
	  grpmean->SetPointError(i, 0, pmeanErr[i]);

	  TH1F* hpEp = (TH1F*)( fdcom->FindObjectAny("HP_Pos_cms"));
	  RooCBShape pdf_pEp("pdf_pEp", "PDF_pEp", x, m1, s1, a, n);
	  RooDataHist data_pEp("HP", "dataset with x", x, hpEp);
	  pdf_pEp.fitTo(data_pEp, RooFit::PrintLevel(-1), RooFit::Range(xminFit, xmaxFit));
	  ppos[i] = m1.getVal();
	  pposErr[i] = m1.getError();
	  grppos->SetPoint(i, (double)run, ppos[i]);
	  grppos->SetPointError(i, 0, pposErr[i]);

	  TH1F* hpEm = (TH1F*)( fdcom->FindObjectAny("HP_Neg_cms"));
	  RooCBShape pdf_pEm("pdf_pEm", "PDF_pEm", x, m1, s1, a, n);
	  RooDataHist data_pEm("HP", "dataset with x", x, hpEm);
	  pdf_pEm.fitTo(data_pEm, RooFit::PrintLevel(-1), RooFit::Range(xminFit, xmaxFit));
	  pneg[i] = m1.getVal();
	  pnegErr[i] = m1.getError();
	  grpneg->SetPoint(i, (double)run, pneg[i]);
	  grpneg->SetPointError(i, 0, pnegErr[i]);

	  TH1F* hpLab = (TH1F*)( fdcom->FindObjectAny("HP"));
	  RooDataHist data_plab("HP", "dataset with x", x, hpLab);
	  RooCBShape pdf_plab("pdf_plab", "PDF_plab", x, m1, s1, a, n);
	  pdf_plab.fitTo(data_plab, RooFit::PrintLevel(-1));
	  plab[i] = (s1.getVal())*1000.0;
	  plabErr[i] = (s1.getError())*1000.0;
	  grmom->SetPoint(i, (double)run, plab[i]);
	  grmom->SetPointError(i, 0, plabErr[i]);

	  TH1F* heff = (TH1F*)( fdcom->FindObjectAny("HNtrack"));
	  int ntrk2 = (int)heff->GetBinContent(3);
	  int ntot = (int)heff->GetEntries();
	  effRec[i] = (double)ntrk2 / (double)ntot;
	  effRecErr[i] = sqrt(effRec[i]*(1-effRec[i])/(double)ntot);
	  greff->SetPoint(i, (double)run, effRec[i]);
	  greff->SetPointError(i, 0, effRecErr[i]);

	  TH1F* hbbTrkFlg = (TH1F*)( fdcom->FindObjectAny("BbTrkFlg"));
	  int ibbbin = (int)hbbTrkFlg->GetMaximumBin();
	  int nbb = (int)hbbTrkFlg->GetBinContent(ibbbin);
	  int ntesall = (int)htes->GetEntries();
	  bbeffRec[i] = (double)nbb / (double)ntesall;
	  bbeffRecErr[i] = sqrt(bbeffRec[i]*(1-bbeffRec[i])/(double)ntesall);
	  grbbeff->SetPoint(i, (double)run, bbeffRec[i]);
	  grbbeff->SetPointError(i, 0, bbeffRecErr[i]);

	  TH1F* hcal = (TH1F*)( fdcom->FindObjectAny("HNhitsCal"));
	  int ntrkcal = (int)hcal->GetEntries();
	  effCal[i] = 0.5*(double)ntrkcal / (double)ntot;
	  effCalErr[i] = sqrt(effCal[i]*(1-effCal[i])/(double)ntot);
	  grcal->SetPoint(i, (double)run, effCal[i]);
	  grcal->SetPointError(i, 0, effCalErr[i]);

	  TH1F* hhitEffAll = (TH1F*)( fdcom->FindObjectAny("hitEffAll"));
	  int nhitAll1 = (int)hhitEffAll->GetBinContent(6797);
	  int nhitAll2 = (int)hhitEffAll->GetBinContent(6798);
	  int nhitAll3 = (int)hhitEffAll->GetBinContent(6799);
	  //  int nhitAll3 = (int)hhitEffAll->GetBinContent(6796);

//         TH1F* hhitEffRaw = (TH1F*)( fdcom->FindObjectAny("hitEffRaw"));
	  TH1F* hhitEffRaw = (TH1F*)( fdcom->FindObjectAny("hitEffRec"));
	  int nhitRaw1 = (int)hhitEffRaw->GetBinContent(6797);
	  int nhitRaw2 = (int)hhitEffRaw->GetBinContent(6798);
	  int nhitRaw3 = (int)hhitEffRaw->GetBinContent(6799);
	  // int nhitRaw3 = (int)hhitEffRaw->GetBinContent(6796);
	  effDet1[i] = (double)nhitRaw1 / (double)nhitAll1;
	  effDet2[i] = (double)nhitRaw2 / (double)nhitAll2;
	  effDet3[i] = (double)nhitRaw3 / (double)nhitAll3;
	  if(effDet1[i]>0.9999) effDet1[i] = effDet1[i-1];
	  if(effDet2[i]>0.99) effDet2[i] = effDet2[i-1];
	  if(effDet3[i]>0.9999) effDet3[i] = effDet3[i-1];

	  effDet1Err[i] = sqrt(effDet1[i]*(1-effDet1[i])/(double)nhitAll1);
	  effDet2Err[i] = sqrt(effDet2[i]*(1-effDet2[i])/(double)nhitAll2);
	  effDet3Err[i] = sqrt(effDet3[i]*(1-effDet3[i])/(double)nhitAll3);
	  grdet1->SetPoint(i, (double)run, effDet1[i]);
	  grdet1->SetPointError(i, 0, effDet1Err[i]);
	  grdet2->SetPoint(i, (double)run, effDet2[i]);
	  grdet2->SetPointError(i, 0, effDet2Err[i]);
	  grdet3->SetPoint(i, (double)run, effDet3[i]);
	  grdet3->SetPointError(i, 0, effDet3Err[i]);

	  TH1F* hhit = (TH1F*)( fdcom->FindObjectAny("nRawHit"));
	  if(hhit != NULL){
	       int nNoise = 0;
	       int nEvtTot = (int)hhit->GetEntries();
	       int nbin = (int)hhit->GetNbinsX();
	       for(int ibin=0; ibin<nbin; ibin++){
		    double bincen = hhit->GetBinCenter(ibin);
		    if(bincen > 1000){
			 int nBinCon = (int)hhit->GetBinContent(ibin);
			 nNoise += nBinCon;
		    }
	       }
	       noiseRatio[i] = (double)nNoise / (double)nEvtTot;
	       noiseRatioErr[i] = sqrt(noiseRatio[i]*(1-noiseRatio[i])/(double)nEvtTot);
	  } else{
	       noiseRatio[i] = 1.2;
	       noiseRatioErr[i] = 0;
	  }
	  grhit->SetPoint(i, (double)run, noiseRatio[i]);
	  grhit->SetPointError(i, 0, noiseRatioErr[i]);

	  TH1F* hz0 = (TH1F*)( fdcom->FindObjectAny("dz"));
	  int nz0 = (int)hz0->GetEntries();
	  if(nz0>100){
	       hz0->Fit("gaus","Q");
	       z0[i] = hz0->GetFunction("gaus")->GetParameter(1);
	       z0sig[i] = hz0->GetFunction("gaus")->GetParameter(2);
	       z0err[i] = hz0->GetFunction("gaus")->GetParError(1);
	       z0sigerr[i] = hz0->GetFunction("gaus")->GetParError(2);
//	z0[i] /= 10.0;
//	z0err[i] /= 10.0;
//	z0sig[i] /= 10.0;
//	z0sigerr[i] /= 10.0;
	  } else{
	       z0[i] = 0.0;
	       z0sig[i] = 0.0;
	       z0err[i] = 0.0;
	       z0sigerr[i] = 0.0;
	  }
	  grz0->SetPoint(i, (double)run, z0[i]);
	  grz0->SetPointError(i, 0, z0err[i]);
	  grz0sig->SetPoint(i, (double)run, z0sig[i]);
	  grz0sig->SetPointError(i, 0, z0sigerr[i]);

	  double pcmsMin = 4.0;
	  double pcmsMax = 14.0;
	  if( (run >= 47467) && (run <= 47493) ){
	       pcmsMin = 11.0;
	       pcmsMax = 14.0;
	  } else if( (run >= 47494) && (run <= 47505) ){
	       pcmsMin = 11.5;
	       pcmsMax = 15.0;
	  } else if( (run >= 47543) && (run <= 51498) ){
	       pcmsMin = 14.0;
	       pcmsMax = 17.0;
	  } else if( (run >= 51499) && (run <= 56768) ){
	       pcmsMin = 10.0;
	       pcmsMax = 14.0;
	  } else if( (run >= 56769) && (run <= 59162)){
	       pcmsMin = 7.0;
	       pcmsMax = 14.0;
	  }else if( (run >= 59163)&& (run <= 59896)){
		   pcmsMin = 13.0;
		   pcmsMax = 16.0;
	  }else if( (run <= 66224)){
		   pcmsMin = 15.0;
		   pcmsMax = 21.0;
	  }else if( (run <= 81810)){
		   pcmsMin = 10.0;
		   pcmsMax = 15.0;
	  }else if( (run <= 100000)){
		   pcmsMin = 3.0;
		   pcmsMax = 8.0;
	  }
	  if( (rms[i]<110.) || (rms[i]>140.) || (pcms[i]<pcmsMin) || (pcms[i]>pcmsMax) ){
	       runFlag[i] = "FAIL";
	       cout << setw(20) << pcmsMin << setw(20) << pcmsMax << endl;
	       cout << "FAIL:  " << setw(20)<<"rms:\t" << rms[i] << setw(20)<<"pcms:\t" << pcms[i] << endl;
	  }
	  else runFlag[i] = "GOOD";

	  i++;
     }
	 // double aver_reco ;
	 // aver_reco= reco_total/i;
	 // cout<<"aver_reco"<<aver_reco<<"\ti"<<i<<endl;
     int nFileAll = i;

     cout << "nfile: " << nFileAll << endl;
     ofstream fout("fitResults.txt", ios::app);
     for(i=0; i<nFileAll; i++){
	  if(!runwrt[i]) continue;
	  fout << setw(7) << runnum[i] << setw(6) << runFlag[i] << setw(15) << reso[i]
	       << setw(15) << rms[i] << setw(15) << plab[i] << setw(15) << plabErr[i]
	       << setw(15) << pcms[i] << setw(15) << pcmsErr[i] << endl;
	  fout << setw(28) << pmean[i] << setw(15) << pmeanErr[i]
	       << setw(15) << ppos[i] << setw(15) << pposErr[i]
	       << setw(15) << pneg[i] << setw(15) << pnegErr[i] << endl;
	  fout << setw(28) << effRec[i] << setw(15) << effRecErr[i]
	       << setw(15) << bbeffRec[i] << setw(15) << bbeffRecErr[i]
	       << setw(15) << effCal[i] << setw(15) << effCalErr[i] << endl;
	  fout << setw(28) << effDet1[i] << setw(15) << effDet1Err[i]
	       << setw(15) << effDet2[i] << setw(15) << effDet2Err[i]
	       << setw(15) << effDet3[i] << setw(15) << effDet3Err[i] << endl;
	  fout << setw(28) << noiseRatio[i] << setw(15) << noiseRatioErr[i]
	       << setw(15) << z0[i] << setw(15) << z0err[i]
	       << setw(15) << z0sig[i] << setw(15) << z0sigerr[i] << endl;
	  cout << "Add run " << runnum[i] << " to fitResults.txt" << endl;
     }
     fout.close();

     TCanvas* c1 = (TCanvas*)(gROOT->GetListOfCanvases()->FindObject("c1"));
     if(c1 != NULL) c1->Close();

     TCanvas c0("Spatial resolution", "residual", 10, 10, 750, 500);
     h2->SetXTitle("Run");
     h2->SetYTitle("Spatial resolution (#mum)");
     h2->GetXaxis()->CenterTitle();
     h2->GetYaxis()->CenterTitle();

     h2->Draw();
     grreso->Draw("p");
     //      sprintf(fname, "resiVsRun%d_%d.eps", runmin, runmax);
     //      c1.Print(fname);

     //      TCanvas c2("pLab", "pLab", 10, 10, 750, 500);
     //		h3->SetXTitle("Run");
     //		h3->SetYTitle("pLab(GeV/c)");
     //		h3->GetXaxis()->CenterTitle();
     //		h3->GetYaxis()->CenterTitle();
     //      h3->Draw();
     //      grmom->Draw("p");
     //      sprintf(fname, "pLabVsRun%d_%d.eps", runmin, runmax);
     //      c2.Print(fname);

     TCanvas c4("pcms", "pcms", 10, 10, 750, 500);
     h4->SetXTitle("Run");
     h4->SetYTitle("#sigmaP(MeV/c)");
     h4->GetXaxis()->CenterTitle();
     h4->GetYaxis()->CenterTitle();
     h4->Draw();
     grmomcms->Draw("p");
     //      sprintf(fname, "pcmsVsRun%d_%d.eps", runmin, runmax);
     //      c4.Print(fname);

     TCanvas c5("pmean", "pmean", 10, 10, 750, 500);
     h5->SetXTitle("Run");
     h5->SetYTitle("P(GeV/c)");
     h5->GetXaxis()->CenterTitle();
     h5->GetYaxis()->CenterTitle();
     h5->Draw();
     grpmean->Draw("p");
     //      sprintf(fname, "pmeanVsRun%d_%d.eps", runmin, runmax);
     //      c5.Print(fname);

     TCanvas c6("epem", "epem", 10, 10, 750, 500);
     h5->SetXTitle("Run");
     h5->SetYTitle("P(GeV/c)");
     h5->GetXaxis()->CenterTitle();
     h5->GetYaxis()->CenterTitle();
     h5->Draw();
     grppos->Draw("p");
     grpneg->Draw("p");
     //      sprintf(fname, "epemVsRun%d_%d.eps", runmin, runmax);
     //      c6.Print(fname);

//     TCanvas c7("eff", "eff", 10, 10, 750, 500);
//		h6->SetXTitle("Run");
//		h6->SetYTitle("effcal");
//		h6->GetXaxis()->CenterTitle();
//		h6->GetYaxis()->CenterTitle();
//     h6->Draw();
//     greff->Draw("p");

//     TCanvas c8("effcal", "effcal", 10, 10, 750, 500);
//		h7->SetXTitle("Run");
//		h7->SetYTitle("effcal");
//		h7->GetXaxis()->CenterTitle();
//		h7->GetYaxis()->CenterTitle();
//     h7->Draw();
//     grcal->Draw("p");

//     TCanvas c9("hit", "hit", 10, 10, 750, 500);
//		h8->SetXTitle("Run");
//		h8->SetYTitle("hit");
//		h8->GetXaxis()->CenterTitle();
//		h8->GetYaxis()->CenterTitle();
//     h8->Draw();
//     grhit->Draw("p");

     TCanvas c10("effmdcrec", "effmdcrec", 10, 10, 750, 500);
     h9->SetXTitle("Run");
     h9->SetYTitle("effmdcrec");
     h9->GetXaxis()->CenterTitle();
     h9->GetYaxis()->CenterTitle();
     h9->Draw();
     grbbeff->Draw("p");

     TCanvas c11("HitEff", "HitEff", 10, 10, 750, 500);
     h9_2->SetXTitle("Run");
     h9_2->SetYTitle("Hit efficiency after track finding");
     h9_2->GetXaxis()->CenterTitle();
     h9_2->GetYaxis()->CenterTitle();
     h9_2->Draw();
     // grdet1->Draw("p");
     grdet2->Draw("p");
     grdet3->Draw("p");

     TLegend *leg=new TLegend(0.4,0.4,0.6,0.6);
     leg->SetBorderSize(1);
     leg->SetTextFont(42);
     leg->SetFillColor(10);
     // leg->AddEntry(grdet1,"inner", "p");
     leg->AddEntry(grdet2,"step", "p");
     leg->AddEntry(grdet3,"outer", "p");
     leg->Draw();

     TCanvas c12("z0", "z0", 10, 10, 750, 500);
     h10->SetXTitle("Run");
     h10->SetYTitle("z0(mm)");
     h10->GetXaxis()->CenterTitle();
     h10->GetYaxis()->CenterTitle();
     h10->Draw();
     grz0->Draw("p");

//     TCanvas c13("z0sigma", "z0sigma", 10, 10, 750, 500);
//		h11->SetXTitle("Run");
//		h11->SetYTitle("#sigmaz0(mm)");
//		h11->GetXaxis()->CenterTitle();
//		h11->GetYaxis()->CenterTitle();
//     h11->Draw();
//     grz0sig->Draw("p");
	 
	 //pdf generating
	 char pdfFileName[200];
	 sprintf(pdfFileName, "noise_%d_%d.pdf", runmin, runmax);
	 c0.Print(Form("%s(", pdfFileName));
	 c4.Print(pdfFileName);
	 c5.Print(pdfFileName);
	 c6.Print(pdfFileName);
	 c10.Print(pdfFileName);
	 c11.Print(pdfFileName);
	 c12.Print(pdfFileName);
	 c12.Print(Form("%s)", pdfFileName));
    
     return 0;
}
