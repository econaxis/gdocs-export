#include <vector>
#include "pybind11/pybind11.h"
#include "json/json.hpp"




using json=nlohmann::json;
using py=pybind11;

struct Operation {
    std::tuple<long, long> len;
    long time = 0;

    auto round(const long& start) {
        return static_cast<unsigned long>((time-start)/30.F);
    };

    Operation& operator +=(const Operation& rhs) {
        auto &[adds, deletes] = this->len;
        auto &[radds, rdeletes] = rhs.len;
        adds += radds;
        deletes+=rdeletes;
        this->time = rhs.time;
        return *this;
    };

    
};


PYBIND11_MODULE(example, m) {
    py::class_<Fds>(m, "Operation");
};

auto work = std::vector<json>{};

auto ops = std::vector<Operation>{};


namespace o {
auto o() {
    for (auto x : work) {
        if(/*!x.contains(0) ||*/ x[0]["ty"] == "is" || x[0]["ty"] == "ds" ||x[0]["ty"] == "mllti") {
            continue;
        }

        auto ty = x[0].get<std::string>();

        if (ty == "mlti") {
            for (auto &i:x[0]["mts"]) {
                work.push_back(json{i, x[1]});
            }
            continue;
        }

        auto content_length = std::tuple<long, long>{0L, 0L};

        if (ty == "is") {
            auto&& ad_len = x[0]["s"].get<long>();
            content_length = {ad_len+1, 0};
        } else if (ty == "ds") {
            auto&& del_len = x[0]["ei"].get<long>() - x[0]["si"].get<long>() + 1;
            content_length = {0, del_len};
        }

        auto &&time = static_cast<long>(x[1].get<long>() / 1e3L);
        ops.push_back(Operation{content_length, time});
    }

    auto ops_cond = std::vector<Operation>{};

    auto start_ind = ops[0].time;
    ops_cond.resize(static_cast<std::size_t>((ops.back().time - start_ind ) / 30), Operation{{0, 0}, start_ind});
    
    for (auto &op : ops) {
        ops_cond[op.round(start_ind)] += op;
    };

    return ops_cond;

    }
};


int main() {
    o::o();
};
