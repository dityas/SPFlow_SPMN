'''
Created on March 22, 2018

@author: Alejandro Molina
'''
import subprocess

from spn.io.Text import to_str_equation
from spn.structure.Base import get_nodes_by_type, Leaf


def to_cpp(node, leaf_to_cpp):
    vartype = "double"

    spn_eqq = to_str_equation(node, {Leaf: lambda node, _: "leaf_node_%s(data[i][%s])" % (id(node), node.scope[0])})

    spn_function = """
    {vartype} likelihood(int i, {vartype} data[][{scope_size}]){{
        return {spn_eqq};
    }}
    """.format(vartype=vartype, scope_size=len(node.scope), spn_eqq=spn_eqq)

    init_code = ""
    leaves_functions = ""
    for l in get_nodes_by_type(node, Leaf):
        leaf_name = "leaf_node_%s" % (id(l))
        leave_function, leave_init = leaf_to_cpp(l, leaf_name, vartype)

        leaves_functions += leave_function
        init_code += leave_init

    return """
#include <iostream>
#include <string>
#include <vector>
#include <boost/algorithm/string.hpp>
#include <boost/lexical_cast.hpp>
#include <iomanip>
#include <chrono>


using namespace std;

{leaves_functions}

{spn_function}

int main() 
{{

    {init_code}
 
    vector<string> lines;
    for (string line; getline(std::cin, line);) {{
        lines.push_back( line );
    }}
    
    int n = lines.size()-1;
    int f = {scope_size};
    {vartype} data[n][{scope_size}];
    
    for(int i=0; i < n; i++){{
        std::vector<std::string> strs;
        boost::split(strs, lines[i+1], boost::is_any_of(";"));
        
        for(int j=0; j < f; j++){{
            data[i][j] = boost::lexical_cast<{vartype}>(strs[j]);
        }}
    }}
    
    {vartype} result[n];
    
    chrono::high_resolution_clock::time_point begin = chrono::high_resolution_clock::now();
    for(int j=0; j < 10000; j++){{
        for(int i=0; i < n; i++){{
            result[i] = likelihood(i, data);
        }}
    }}
    chrono::high_resolution_clock::time_point end = chrono::high_resolution_clock::now();

    long double avglikelihood = 0;
    for(int i=0; i < n; i++){{
        avglikelihood += log(result[i]);
        cout << setprecision(60) << log(result[i]) << endl;
    }}

    cout << setprecision(15) << "avg ll " << avglikelihood/n << endl;
    
    cout << "size of variables " << sizeof({vartype}) * 8 << endl;

    cout << setprecision(15)<< "time per instance " << (chrono::duration_cast<chrono::nanoseconds>(end-begin).count()  / 10000.0) /n << " ns" << endl;
    cout << setprecision(15) << "time per task " << (chrono::duration_cast<chrono::nanoseconds>(end-begin).count()  / 10000.0)  << " ns" << endl;


    return 0;
}}
    """.format(spn_function=spn_function, vartype=vartype, leaves_functions=leaves_functions,
               scope_size=len(node.scope), init_code=init_code)


def generate_native_executable(spn, leaf_to_cpp, cppfile="/tmp/spn.cpp", nativefile="/tmp/spnexe"):
    code = to_cpp(spn, leaf_to_cpp)

    text_file = open(cppfile, "w")
    text_file.write(code)
    text_file.close()

    nativefile_fast = nativefile + '_fastmath'

    return subprocess.check_output(['g++', '-O3', '--std=c++11', '-o', nativefile, cppfile],
                                   stderr=subprocess.STDOUT).decode("utf-8"), \
           subprocess.check_output(['g++', '-O3', '-ffast-math', '--std=c++11', '-o', nativefile_fast, cppfile],
                                    stderr=subprocess.STDOUT).decode("utf-8"), \
           code
