#pragma once
#include <string>
#include <vector>
#include <utility>
#include "global.h"
#include "objects.h"
#include "placedb.h"

class OpenroadInterface {
public:
    OpenroadInterface(PlaceDB *_db)
    {
        db = _db;
    }
    void intializePaths(std::string eGPdefPath, std::string openroadPath, std::string tclPath, std::string staReportPath)
    {
        DEFAULTeGPdefPath = eGPdefPath;
        DEFAULTopenroadPath = openroadPath;
        DEFAULTtclPath = tclPath;
        DEFAULTstaReportPath = staReportPath;
        DEFAULTTNS = 100000.0f;
        DEFAULTWNS = 300.0f;
    }

    bool runSTA ( std::string eGPdefPath, std::string openroadPath, std::string tclPath,  std::string staReportPath);
    void analyzeSTAReport(std::string staReportPath);
    void outputSTADEF(std::string initialDEFPath , std::string outputDEFPath);

private:
    PlaceDB *db;
    std::string DEFAULTeGPdefPath; // 路徑用於存儲eplace glbal placement DEF文件
    std::string DEFAULTstaReportPath; // 路徑用於存儲報告
    std::string DEFAULTtclPath; // 用於存儲TCL腳本的路徑
    std::string DEFAULTopenroadPath; 

    float DEFAULTTNS, DEFAULTWNS;
};
