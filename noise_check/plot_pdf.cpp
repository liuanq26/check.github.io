#include <iostream>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <cmath>
#include <cstdio>
#include <unistd.h>

#include "TFile.h"
#include "TFolder.h"
#include "TH1F.h"
#include "TH2F.h"
#include "TGraph.h"
#include "TLegend.h"
#include "TCanvas.h"
#include "TStyle.h"

const int nWireStp = 1288;
const int nWireOut = 5024;
const char* RESULTS_FILE = "noiseResults.txt";

using namespace std;

static TGraph* make_graph(const char* name, int color)
{
    TGraph* g = new TGraph();
    g->SetName(name);
    g->SetMarkerStyle(20);
    g->SetMarkerColor(color);
    return g;
}

static TGraph* load_graph(TFile& f, const char* name, int color)
{
    TGraph* src = (TGraph*)f.Get(name);
    if (!src) return make_graph(name, color);
    TGraph* g = new TGraph(*src);
    g->SetName(name);
    g->SetMarkerStyle(20);
    g->SetMarkerColor(color);
    return g;
}

static void load_results(const char* path, map<int, string>& lines)
{
    ifstream in(path);
    if (!in) return;
    string line;
    while (getline(in, line)) {
        istringstream iss(line);
        int run;
        if (iss >> run) lines[run] = line;
    }
}

static void save_results(const char* path, const map<int, string>& lines)
{
    ofstream out(path);
    out << "# BESIII MDC noise per-run results\n";
    out << "# run flag nevents key=value ...\n";
    map<int, string>::const_iterator it;
    for (it = lines.begin(); it != lines.end(); ++it) {
        out << it->second << "\n";
    }
}

int main(int argc, char* argv[])
{
    char path[512];
    int runmin, runmax;

    if (argc > 3) {
        sscanf(argv[1], "%511s", path);
        sscanf(argv[2], "%d", &runmin);
        sscanf(argv[3], "%d", &runmax);
    } else {
        cout << "usage: plot_pdf <hist_dir> <runmin> <runmax>" << endl;
        return -1;
    }

    // colors: step, outer, unused
    int col[] = {kGreen + 2, kAzure + 2, kMagenta - 7};

    gStyle->SetPadLeftMargin(0.15);
    gStyle->SetPadBottomMargin(0.15);
    gStyle->SetPadRightMargin(0.05);
    gStyle->SetPadTopMargin(0.05);
    gStyle->SetFrameLineWidth(2);
    gStyle->SetCanvasColor(10);
    gStyle->SetPadGridY(1);
    gStyle->SetTitleXSize(0.06);
    gStyle->SetTitleXOffset(1);
    gStyle->SetTitleYSize(0.06);
    gStyle->SetTitleYOffset(1);
    gStyle->SetTitleFont(42, "xyz");
    gStyle->SetStatFont(42);
    gStyle->SetLabelFont(42, "xyz");
    gStyle->SetLabelSize(0.055, "xyz");
    gStyle->SetLabelOffset(0.01, "xyz");
    gStyle->SetNdivisions(505, "xyz");

    TH2F* h1 = new TH2F("h1", "", 500, runmin - 5, runmax + 5, 100, 0, 0.1);
    h1->SetStats(0);
    h1->GetXaxis()->SetTitle("Run");
    h1->GetYaxis()->SetTitle("Noise occupancy after T&Q match");
    h1->GetXaxis()->CenterTitle();
    h1->GetYaxis()->CenterTitle();

    TH2F* h2 = new TH2F("h2", "", 500, runmin - 5, runmax + 5, 100, 0, 0.1);
    h2->SetStats(0);
    h2->GetXaxis()->SetTitle("Run");
    h2->GetYaxis()->SetTitle("Noise occupancy of T channel");
    h2->GetXaxis()->CenterTitle();
    h2->GetYaxis()->CenterTitle();

    int iRun = 0;
    vector<double> vecRun;
    TGraph* grStp = 0;
    TGraph* grOut = 0;
    TGraph* grRatioStp = 0;
    TGraph* grRatioOut = 0;
    TGraph* grRatioStp_T = 0;
    TGraph* grRatioOut_T = 0;

    if (access("graph.root", 0) == -1) {
        cout << "step1 ---------------------" << endl;
        grStp = make_graph("grStp", col[0]);
        grOut = make_graph("grOut", col[1]);
        grRatioStp = make_graph("grRatioStp", col[0]);
        grRatioOut = make_graph("grRatioOut", col[1]);
        grRatioStp_T = make_graph("grRatioStp_T", col[0]);
        grRatioOut_T = make_graph("grRatioOut_T", col[1]);
    } else {
        cout << "step2 ---------------------" << endl;
        TFile fhist("graph.root");
        if (fhist.IsOpen()) {
            grStp = load_graph(fhist, "grStp", col[0]);
            grOut = load_graph(fhist, "grOut", col[1]);
            grRatioStp = load_graph(fhist, "grRatioStp", col[0]);
            grRatioOut = load_graph(fhist, "grRatioOut", col[1]);
            grRatioStp_T = load_graph(fhist, "grRatioStp_T", col[0]);
            grRatioOut_T = load_graph(fhist, "grRatioOut_T", col[1]);
            fhist.Close();
        } else {
            grStp = make_graph("grStp", col[0]);
            grOut = make_graph("grOut", col[1]);
            grRatioStp = make_graph("grRatioStp", col[0]);
            grRatioOut = make_graph("grRatioOut", col[1]);
            grRatioStp_T = make_graph("grRatioStp_T", col[0]);
            grRatioOut_T = make_graph("grRatioOut_T", col[1]);
        }

        iRun = grStp->GetN();
        for (int i = 0; i < iRun; i++) {
            double x, y;
            grStp->GetPoint(i, x, y);
            vecRun.push_back(x);
        }
    }

    map<int, int> runIndex;
    for (size_t i = 0; i < vecRun.size(); i++) {
        runIndex[(int)(vecRun[i] + 0.5)] = (int)i;
    }

    map<int, string> resultLines;
    load_results(RESULTS_FILE, resultLines);

    TLegend* legTQ = new TLegend(0.70, 0.70, 0.90, 0.90);
    legTQ->SetBorderSize(1);
    legTQ->SetTextFont(42);
    legTQ->SetFillColor(10);
    legTQ->AddEntry(grRatioStp, "Step", "p");
    legTQ->AddEntry(grRatioOut, "Outer", "p");

    TLegend* legT = new TLegend(0.70, 0.70, 0.90, 0.90);
    legT->SetBorderSize(1);
    legT->SetTextFont(42);
    legT->SetFillColor(10);
    legT->AddEntry(grRatioStp_T, "Step", "p");
    legT->AddEntry(grRatioOut_T, "Outer", "p");

    cout << "iRun = " << iRun << endl;

    for (int run = runmin; run <= runmax; run++) {
        char fname[600];
        snprintf(fname, sizeof(fname), "%s/hist%05d.root", path, run);
        if (access(fname, 0) == -1) continue;

        TFile f(fname);
        if (!f.IsOpen()) continue;

        TFolder* fd = (TFolder*)f.Get("all");
        if (!fd) {
            f.Close();
            continue;
        }

        TH1F* hStp = (TH1F*)fd->FindObjectAny("nhitRawStp");
        if (!hStp) {
            f.Close();
            continue;
        }

        int nEvt = (int)hStp->GetEntries();
        if (nEvt < 50) {
            f.Close();
            continue;
        }

        TH1F* hStp_T = (TH1F*)fd->FindObjectAny("nhitRawStpTch");
        TH1F* hOut = (TH1F*)fd->FindObjectAny("nhitRawOut");
        TH1F* hOut_T = (TH1F*)fd->FindObjectAny("nhitRawOutTch");
        if (!hStp_T || !hOut || !hOut_T) {
            cout << "run " << run << " missing one of the noise histograms, skip" << endl;
            f.Close();
            continue;
        }

        double meanStp = hStp->GetMean();
        double meanStp_T = hStp_T->GetMean();
        double meanOut = hOut->GetMean();
        double meanOut_T = hOut_T->GetMean();

        double occStp = (meanStp - 24.0) / (double)nWireStp;
        double occStp_T = (meanStp_T - 24.0) / (double)nWireStp;
        double occOut = (meanOut - 46.0) / (double)nWireOut;
        double occOut_T = (meanOut_T - 46.0) / (double)nWireOut;

        int idx;
        map<int, int>::iterator it = runIndex.find(run);
        if (it == runIndex.end()) {
            idx = iRun++;
            runIndex[run] = idx;
        } else {
            idx = it->second;
        }

        grStp->SetPoint(idx, run, meanStp);
        grOut->SetPoint(idx, run, meanOut);
        grRatioStp->SetPoint(idx, run, occStp);
        grRatioOut->SetPoint(idx, run, occOut);
        grRatioStp_T->SetPoint(idx, run, occStp_T);
        grRatioOut_T->SetPoint(idx, run, occOut_T);

        ostringstream oss;
        oss << setprecision(10)
            << run << " OK " << nEvt
            << " nevents=" << nEvt
            << " nhitStp=" << meanStp
            << " nhitStp_T=" << meanStp_T
            << " nhitOut=" << meanOut
            << " nhitOut_T=" << meanOut_T
            << " occStp=" << occStp
            << " occStp_T=" << occStp_T
            << " occOut=" << occOut
            << " occOut_T=" << occOut_T;
        resultLines[run] = oss.str();

        f.Close();
    }

    TFile fout("graph.root", "recreate");
    grStp->Write("", TObject::kOverwrite);
    grOut->Write("", TObject::kOverwrite);
    grRatioStp->Write("", TObject::kOverwrite);
    grRatioOut->Write("", TObject::kOverwrite);
    grRatioStp_T->Write("", TObject::kOverwrite);
    grRatioOut_T->Write("", TObject::kOverwrite);
    fout.Close();
    cout << "root file has been written." << endl;

    save_results(RESULTS_FILE, resultLines);
    cout << "text results: " << RESULTS_FILE << endl;

    TCanvas c4("outer", "outer", 50, 50, 750, 500);
    c4.SetFillColor(10);
    h1->Draw();
    grRatioStp->Draw("p");
    grRatioOut->Draw("p");
    legTQ->Draw("p");

    TCanvas c5("outer", "outer", 10, 10, 750, 500);
    c5.SetFillColor(10);
    h2->Draw();
    grRatioStp_T->Draw("p");
    grRatioOut_T->Draw("p");
    legT->Draw("p");

    char pdfFileName[200];
    sprintf(pdfFileName, "noise_%d_%d.pdf", runmin, runmax);
    c4.Print(Form("%s(", pdfFileName));
    c5.Print(Form("%s)", pdfFileName));
    cout << "PDF saved as: " << pdfFileName << endl;

    return 0;
}
