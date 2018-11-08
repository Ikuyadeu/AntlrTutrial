"""
Get Style missing from diff file
Style misses list
* Rename identifier
* Large to Small (ex:"Style" to "style")
* only make new line
* Space or Tab
* Don't changed AST

Usage:
python3 src/scget/StyleFromJson.py 0 20000 ./gm_openstack_merge.csv
"""
import csv
import os
import re
import sys
import json
from pyantlr.change_detector import ChangeDetector
import logging
from pylint import epylint as lint
from collections import Counter

logging.basicConfig(filename='ANTLR_STYLE.log',level=logging.DEBUG)

# import time
# from collections import OrderedDict


OUT_METRICSES = ["ch_id",
                 "ch_change_id",
                 "ch_author_account_id",
                 "rev_change_id",
                 "f_file_name",
                ]
JSON_DIR_PATH = ""

OUT_JSON_NAME = "out/out"

def main():
    """
    The main
    """
    if len(sys.argv) > 1:
        in_csv_path = sys.argv[1]
    else:
        print("""Usage: python %s in_csv_path""" % sys.argv[0])
        sys.exit()

    JSON_DIR_PATHES = [
        """/Users/kenjiro/Documents/CollectReviewData_ini/revision_files/gm_openstack0_200000/""",
        """/Users/kenjiro/Documents/CollectReviewData_ini/revision_files/gm_openstack200000_400000/""",
        """/Users/kenjiro/Documents/CollectReviewData_ini/revision_files/gm_openstack400000_600000/""",
        """/Users/kenjiro/Documents/CollectReviewData_ini/revision_files/gm_openstack600000_900000/""",
        """/Users/kenjiro/Documents/CollectReviewData_ini/revision_files/gm_openstack900000_1100000/""",
        """/Users/kenjiro/Documents/CollectReviewData_ini/revision_files/gm_openstack1100000_1500000/""",
        """/Users/kenjiro/Documents/CollectReviewData_ini/revision_files/gm_openstack2000000_2500000/""",
        """/Users/kenjiro/Documents/CollectReviewData_ini/revision_files/gm_openstack2500000_3000000/""",
        """/Users/kenjiro/Documents/CollectReviewData_ini/revision_files/gm_openstack3000000_3500000/""",
        """/Users/kenjiro/Documents/CollectReviewData_ini/revision_files/gm_openstack3500000_4000000/""",
        """/Users/kenjiro/Documents/CollectReviewData_ini/revision_files/gm_openstack4000000_4250000/""",
        """/Users/kenjiro/Documents/CollectReviewData_ini/revision_files/gm_openstack4250000_4500000/"""
    ]

    # JSON_DIR_PATHES = ["""json/gm_openstack/"""]

    # JSON_DIR_PATH = """/Users/kenjiro/Documents/CollectReviewData_ini/revision_files/gm_openstack""" + pathNo + """/"""

    CD = ChangeDetector("", "")

    def makeChangeSet(code_a, code_b):
        change_set = {
            "a": getTokens(code_a),
            "b": getTokens(code_b)
        }
        return change_set

    def getTokens(code):
        def abstractTokens(tokens):
            return [x["token"] if x["element"] in ["<INVALID>", "NAME"] else x["element"] 
            for x 
            in tokens]
        tokens = []
        for token in CD.getTokens(code):
            tokens.append({
                "token": token[0],
                "element": token[1],
            })
        code_info = {
            "base_code": code,
            # "tokens": tokens,
            "abstracted_tokens": abstractTokens(tokens)
        }
        return code_info

    with open(in_csv_path, "r") as in_csv_file:
        reader = csv.DictReader(in_csv_file)
        reader = [i for i in reader if i["f_file_name"].endswith(".py") ]

    out_count = 0
    changes_sets = []
    out_name = OUT_JSON_NAME + "_0.json"
    current_name = out_name
    # out_json_file = open(out_name, "w", encoding='utf-8')

    for line in reader:
        is_file = False
        json_path = ""
        for j_p in JSON_DIR_PATHES:
            json_path = j_p + line["rev_id_y"] + "/" + line["f_file_name"] + ".json"
            if os.path.isfile(json_path):
                is_file = True
                break

        if not is_file:
            continue

        with open(json_path, "r") as target:
            try:
                data = json.load(target)
            except json.decoder.JSONDecodeError:
                continue

            if data["change_type"] != "MODIFIED":
                continue
            content = data["content"]
            if any([("skip" in i) for i in content]):
                continue
            # sys.stdout.write("\rChange: %s / %d: %s" % (line["rev_change_id"], max_pull_no, line["f_file_name"]))

        out_metricses = {}
        for metric in OUT_METRICSES:
            out_metricses[metric] = line[metric]

        # changed_range = get_ori_changed_range(line["rev_id.x"], line["f_file_name"])
        current_line = 0
        for con in content:

            if "ab" in con:
                current_line += len(con["ab"])
                continue
            elif "a" in con:
                content_a = con["a"]
                current_line += len(content_a)
            else:
                continue

            if not "b" in con:
                continue

            # changed_line = range(current_line, current_line + len(content_a))
            content_b = con["b"]

            # out_metricses["changed"] = bool(set(changed_line) & set(changed_range))

            original_a = get_original_content(content_a)
            original_b = get_original_content(content_b)

            try:
                out_metricses["change_set"] = makeChangeSet(original_a, original_b)

            except:
                logging.info("A")
                logging.error(original_a)
                logging.info("B")
                logging.error(original_b)
                continue
            # if max(len(out_metricses["change_set"]["a"]["abstracted_tokens"]), len(out_metricses["change_set"]["b"]["abstracted_tokens"])) > 50:
            #     continue
            out_count += 1
            out_metricses["id"] = str(out_count)

            changes_sets.append(out_metricses)
            # with open(out_name, "w", encoding='utf-8') as f:
            #     json.dump(changes_sets, f, indent = 2)

            out_name = OUT_JSON_NAME + "_" + str(int(out_count / 1000)) + ".json"
            if out_name != current_name:
                print(str(int(out_count / 1000)))
                with open(out_name, "w",encoding='utf-8') as f:
                    json.dump(changes_sets, f, indent = 1)
                current_name = out_name
                changes_sets = []


def get_original_content(content):
    """
    Return original string
    """
    return "\n".join(content)

if __name__ == '__main__':
    main()
