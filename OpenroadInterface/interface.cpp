#include <fstream>
#include <cstdlib>
#include <iostream>
#include "interface.h"


bool OpenroadInterface::runSTA(std::string staDEFPath)
{
    // 檢查 OpenROAD 執行檔是否存在
    if (system((DEFAULTopenroadPath + " -version > /dev/null 2>&1").c_str()) != 0) {
        std::cerr << "[ERROR] OpenROAD binary not found or not executable.\n";
        return false;
    }

    // 生成 eval_sta.tcl
    std::ofstream tclFile(DEFAULTtclPath);
    if (!tclFile.is_open()) {
        std::cerr << "[ERROR] Cannot open TCL path for writing: " << DEFAULTtclPath << "\n";
        return false;
    }

    tclFile << R"(
foreach libFile [glob "../ASAP7/LIB/*nldm*.lib"] {
    puts "lib: $libFile"
    read_liberty $libFile
}
puts "reading lef.."
read_lef ../ASAP7/techlef/asap7_tech_1x_201209.lef
foreach lef [glob "../ASAP7/LEF/*.lef"] {
    read_lef $lef
}
puts "reading def.."
read_def )" << staDEFPath << R"(

read_sdc ../aes_cipher_top/aes_cipher_top.sdc
source ../ASAP7/setRC.tcl

estimate_parasitics -placement

report_tns
report_wns
report_checks -slack_max 0 -endpoint_path_count 10000 -unique_paths_to_endpoint   
exit )";

    tclFile.close();

    // 組合系統命令
    std::stringstream cmd;
    cmd << DEFAULTopenroadPath << " " << DEFAULTtclPath << " > " << DEFAULTstaReportPath;

    std::cout << "[INFO] Running OpenROAD STA...\n";
    int ret = system(cmd.str().c_str());

    if (ret != 0) {
        std::cerr << "[ERROR] OpenROAD execution failed with code: " << ret << "\n";
        return false;
    }

    std::cout << "[INFO] STA completed. Report generated: " << DEFAULTstaReportPath << "\n";
    return true;
}

void OpenroadInterface::analyzeSTAReport()
{
    // If staReportPath is empty, use the default path
    std::string staReportPath = DEFAULTstaReportPath;

    std::ifstream fin(staReportPath);
    if (!fin.is_open()) {
        std::cerr << "Failed to open " << staReportPath << "\n";
        return;
    }

    std::string line;
    std::regex startpoint_regex("^Startpoint: (\\S+)");
    std::regex endpoint_regex("^Endpoint: (\\S+)");
    std::regex pin_regex("^\\s*[-+]?\\d+\\.\\d+\\s+\\d+\\.\\d+\\s+[v\\^]\\s+(\\S+)/(\\S+)");
    std::regex slack_regex("^\\s*(-?\\d+\\.\\d+)\\s+slack");

    std::string start_node, end_node;
    float slack = 0.0f;
    float WNS = DEFAULTWNS;//
    std::vector<std::pair<std::string, std::string>> pathPins;

    while (std::getline(fin, line)) {
        std::smatch match;
        if (std::regex_search(line, match, startpoint_regex)) {
            pathPins.clear();  // reset
            start_node = match[1].str();
        }
        else if (std::regex_search(line, match, endpoint_regex)) {
            end_node = match[1].str();
        }
        else if (std::regex_search(line, match, pin_regex)) {
            std::string node = match[1].str();
            std::string pin = match[2].str();
            pathPins.emplace_back(node, pin);
        }
        else if (std::regex_search(line, match, slack_regex)) {
            slack = std::stof(match[1].str());
            for (size_t i = 1; i < pathPins.size(); ++i) {
                auto [node1, pin1] = pathPins[i - 1];
                auto [node2, pin2] = pathPins[i];
                db->updateP2Pweight(node1, pin1, node2, pin2, slack, WNS);
            }
        }
    }

    fin.close();
}

void OpenroadInterface::outputSTADEF(std::string outputDEFPath)
{
    std::ifstream in(DEFAULTinitialDEFPath);
    if (!in.is_open()) {
        std::cerr << "Failed to open initial DEF file: " << DEFAULTinitialDEFPath << "\n";
        return;
    }

    std::ofstream out(outputDEFPath);
    if (!out.is_open()) {
        std::cerr << "Failed to open output DEF file: " << outputDEFPath << "\n";
        return;
    }
    string line;
    bool inComponent = false;
    int componentCount = 0;
    stringstream ss;

    while (std::getline(in, line)) {
        // Skip the first 4 lines
        if(line.find("COMPONENTS")!=string::npos){
            inComponent = true;
            out << line << endl;
            continue;
        }
        if (line.find("END COMPONENTS") != string::npos) {
            inComponent = false;
            out << line << endl;
            continue;
        }
        if (inComponent) {
            //- g223780 OAI21xp33_ASAP7_75t_SL + PLACED ( 36324 15858 ) N
            //;
            if (line.find("PLACED") != string::npos) {
                componentCount++;
                ss.clear();
                ss.str(line);
                std::string tmp, nodeName , nodetype;
                if (tmp == "-")ss >>tmp >> nodeName >> nodetype; // Get the node name
                else ss >> nodeName >> nodetype;
                
                
                auto module = db->getModuleFromName(nodeName);
                assert(module != nullptr && "Module not found in database");

                out << nodeName << " " << nodetype << " + PLACED ( "
                        << module->getLocation().x << " " << module->getLocation().y << " ) N ;\n";
               
            } 
        }
        out << line << endl; // Write other lines as they are
        
    }
    in.close();
    out.close();
}