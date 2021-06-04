import csv
import json
import os
import subprocess
import time
from argparse import ArgumentParser, Namespace
from typing import List, Dict
from xml.dom import minidom

from xml.parsers.expat import ExpatError

ALL_APPS = ['ActivityDiary', 'AmazeFileManager', 'and-bible', 'AnkiDroid', 'APhotoManager', 'commons',
            'collect', 'FirefoxLite', 'Frost', 'geohashdroid', 'MaterialFBook', 'nextcloud', 'Omni-Notes',
            'open-event-attendee-android', 'openlauncher', 'osmeditor4android', 'Phonograph', 'Scarlet-Notes',
            'sunflower', 'WordPress']


def get_app_name(testing_result_dir):
    for app_name in ALL_APPS:
        if os.path.basename(testing_result_dir).startswith(app_name):
            return app_name
    print("Warning: cannot find app name for this testing result dir: %s" % testing_result_dir)


def get_apk_name(testing_result_dir: str):
    base_name = os.path.basename(testing_result_dir)
    target_apk_file_name = str(base_name.split(".apk")[0]) + ".apk"
    return target_apk_file_name


def get_issue_id(testing_result_dir: str):
    base_name = os.path.basename(testing_result_dir)
    issue_id_str = base_name.split("#")[1].split(".")[0]
    return str(issue_id_str)


def read_coverage_jacoco(jacoco_report_file):
    if not os.path.isfile(jacoco_report_file):
        return False, 0, 0, 0, 0

    try:
        # see the format of coverage report generated by Jacoco in xml
        xmldoc = minidom.parse(jacoco_report_file)
        counters = xmldoc.getElementsByTagName('counter')

        line_coverage = 0
        branch_coverage = 0
        method_coverage = 0
        class_coverage = 0

        for counter in counters:
            type_name = counter.getAttribute('type')
            missed_items = int(counter.getAttribute('missed'))
            covered_items = int(counter.getAttribute('covered'))

            if type_name == 'LINE':
                line_coverage = covered_items * 100.0 / (missed_items + covered_items)

            if type_name == 'BRANCH':
                branch_coverage = covered_items * 100.0 / (missed_items + covered_items)

            if type_name == 'METHOD':
                method_coverage = covered_items * 100.0 / (missed_items + covered_items)

            if type_name == 'CLASS':
                class_coverage = covered_items * 100.0 / (missed_items + covered_items)

        print("-----------")
        print("Line: " + str(line_coverage) + ", Branch: " + str(branch_coverage) + ", Method: " + str(method_coverage)
              + ", Class: " + str(class_coverage))
        print("-----------")
        return True, float("{:.2f}".format(line_coverage)), float("{:.2f}".format(branch_coverage)), \
               float("{:.2f}".format(method_coverage)), float("{:.2f}".format(class_coverage))
    except ExpatError:
        print("*****Parse xml error, catch it!********")
        return False, 0, 0, 0, 0


def get_class_source_files_dirs(app_name, target_apk_file_name):
    class_files = os.path.join("../" + app_name, "class_files.json")
    assert os.path.exists(class_files)

    tmp_file = open(class_files, "r")
    tmp_file_dict = json.load(tmp_file)
    tmp_file.close()

    # Get the class and source files #
    class_source_files_dict = tmp_file_dict[target_apk_file_name]

    class_files_dirs = class_source_files_dict['classfiles']
    source_files_dirs = class_source_files_dict['sourcefiles']

    assert len(class_files_dirs) != 0 and len(source_files_dirs) != 0

    return class_files_dirs, source_files_dirs


def get_class_files_str(app_name, class_files_dirs):
    class_files_dirs_str = ""
    for tmp_dir in class_files_dirs:
        class_files_dirs_str += " --classfiles " + os.path.join("../" + app_name, tmp_dir)
    return class_files_dirs_str


def get_coverage_ec_files_str(coverage_data_dir):
    # Get the coverage data files #
    coverage_ec_files = [os.path.join(coverage_data_dir, f) for f in os.listdir(coverage_data_dir) if
                         os.path.isfile(os.path.join(coverage_data_dir, f)) and f.endswith('.ec')]

    coverage_ec_files_str = ""
    for ec_file in coverage_ec_files:
        coverage_ec_files_str += " " + ec_file

    merged_coverage_ec_file_path = os.path.join(coverage_data_dir, "coverage_all.ec")

    if not os.path.exists(merged_coverage_ec_file_path):
        # only merge when the "coverage_all.ec" does not exist

        merge_cmd = "java -jar ../tools/jacococli.jar merge " + coverage_ec_files_str + \
                    " --destfile " + merged_coverage_ec_file_path
        print('$ %s' % merge_cmd)

        try:
            p = subprocess.Popen(merge_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # clear the output
            output = p.communicate()[0].decode('utf-8').strip()
            print(output)
        except os.error as e:
            print(e)

    return merged_coverage_ec_file_path


def get_coverage_ec_files_str_optimized(coverage_data_dir):
    # Get the coverage data files #
    coverage_ec_files = [os.path.join(coverage_data_dir, f) for f in os.listdir(coverage_data_dir) if
                         os.path.isfile(os.path.join(coverage_data_dir, f)) and f.endswith('.ec')]

    # split the coverage ec files due to the list is too long
    split_size = 30
    coverage_ec_files_list: List[List[str]] = [coverage_ec_files[i:i + split_size] for i in
                                                     range(0, len(coverage_ec_files), split_size)]

    merged_coverage_file_index = 0
    merged_coverage_ec_files = []

    for sublist_coverage_ec_files in coverage_ec_files_list:

        coverage_ec_files_str = ""
        for ec_file in sublist_coverage_ec_files:
            coverage_ec_files_str += " " + ec_file

        merged_coverage_file_index += 1
        merged_coverage_ec_file_path = os.path.join(coverage_data_dir, "coverage_all_" + str(merged_coverage_file_index) + ".ec")

        merge_cmd = "java -jar ../tools/jacococli.jar merge " + coverage_ec_files_str + \
                    " --destfile " + merged_coverage_ec_file_path
        print('$ %s' % merge_cmd)

        try:
            p = subprocess.Popen(merge_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # clear the output
            output = p.communicate()[0].decode('utf-8').strip()
            print(output)

            merged_coverage_ec_files.append(merged_coverage_ec_file_path)

        except os.error as e:
            print(e)

    merged_coverage_ec_files_str = ""
    for ec_file in merged_coverage_ec_files:
        merged_coverage_ec_files_str += " " + ec_file

    return merged_coverage_ec_files_str


def compute_code_coverage(app_name, tool_name, testing_result_dir, coverage_data_dir):
    target_apk_file_name = get_apk_name(testing_result_dir)

    class_files_dirs, source_files_dirs = get_class_source_files_dirs(app_name, target_apk_file_name)

    class_files_dirs_str = get_class_files_str(app_name, class_files_dirs)

    if tool_name == "timemachine":
        coverage_ec_files_str = get_coverage_ec_files_str_optimized(coverage_data_dir)
    else:
        coverage_ec_files_str = get_coverage_ec_files_str(coverage_data_dir)

    # handle the case when no coverage data is available
    if len(coverage_ec_files_str) == 0:
        return False, 0, 0, 0, 0

    # Assemble and execute the coverage computation command #
    xml_coverage_report_file_path = os.path.join(testing_result_dir, "coverage_report.xml")
    cmd = "java -jar ../tools/jacococli.jar report " + coverage_ec_files_str + class_files_dirs_str + " --xml " + \
          xml_coverage_report_file_path
    print('$ %s' % cmd)

    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # clear the output
    output = p.communicate()[0].decode('utf-8').strip()
    print(output)

    return read_coverage_jacoco(xml_coverage_report_file_path)


def compute_single_run_code_coverage(app_name, tool_name, issue_id,
                                     target_app_testing_result_dirs,
                                     coverage_data_summary_file_path):
    for tmp_dir in target_app_testing_result_dirs:

        # only compute coverage for specific issue
        if issue_id is not None and issue_id not in tmp_dir:
            continue

        if tool_name not in tmp_dir:
            # double check to ensure the testing result dir is indeed from the target tool
            continue

        print(tmp_dir)

        if tool_name == "timemachine":
            coverage_data_dir = os.path.join(tmp_dir, "timemachine-output")
        else:
            coverage_data_dir = tmp_dir

        # If is_valid_data is False, it means the no coverage files exists or parsing coverage report failed.
        is_valid_data, line_coverage, branch_coverage, method_coverage, class_coverage = \
            compute_code_coverage(app_name, tool_name, tmp_dir, coverage_data_dir)

        # dump info into csv
        if is_valid_data:
            print("**** Valid data, write to the file ****")
            time.sleep(1)
            with open(coverage_data_summary_file_path, "a") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(
                    [app_name, tool_name, os.path.basename(tmp_dir), line_coverage, branch_coverage, method_coverage,
                     class_coverage])
            csv_file.close()


def compute_average_code_coverage(app_name, tool_name, issue_id,
                                  target_app_testing_result_dirs,
                                  average_coverage_data_summary_file_path):
    average_coverage_dict: Dict[str, Dict[str, List[float]]] = {}

    for tmp_dir in target_app_testing_result_dirs:

        # only compute coverage for specific issue
        if issue_id is not None and issue_id not in tmp_dir:
            continue

        if tool_name not in tmp_dir:
            # double check to ensure the testing result dir is indeed from the target tool
            continue

        print(tmp_dir)

        if tool_name == "timemachine":
            coverage_data_dir = os.path.join(tmp_dir, "timemachine-output")
        else:
            coverage_data_dir = tmp_dir

        # If is_valid_data is False, it means the no coverage files exists or parsing coverage report failed.
        is_valid_data, line_coverage, branch_coverage, method_coverage, class_coverage = \
            compute_code_coverage(app_name, tool_name, tmp_dir, coverage_data_dir)

        # dump info into csv
        if is_valid_data and line_coverage > 0.0:

            # skip ZERO coverage
            issue_id_str = get_issue_id(tmp_dir)
            if issue_id_str not in average_coverage_dict:
                average_coverage_dict[issue_id_str] = {'line': [line_coverage],
                                                       'branch': [branch_coverage],
                                                       'method': [method_coverage],
                                                       'class': [class_coverage]}
            else:
                tmp_coverage_dict = average_coverage_dict[issue_id_str]
                tmp_coverage_dict['line'].append(line_coverage)
                tmp_coverage_dict['branch'].append(branch_coverage)
                tmp_coverage_dict['method'].append(method_coverage)
                tmp_coverage_dict['class'].append(class_coverage)

    for issue_id_str in average_coverage_dict:
        print("**** [%s] Compute average coverage data, write to the file ****" % issue_id_str)
        tmp_coverage_dict = average_coverage_dict[issue_id_str]
        average_line_coverage = "{:.2f}".format(sum(tmp_coverage_dict['line']) / len(tmp_coverage_dict['line']))
        average_branch_coverage = "{:.2f}".format(sum(tmp_coverage_dict['branch']) / len(tmp_coverage_dict['branch']))
        average_method_coverage = "{:.2f}".format(sum(tmp_coverage_dict['method']) / len(tmp_coverage_dict['method']))
        average_class_coverage = "{:.2f}".format(sum(tmp_coverage_dict['class']) / len(tmp_coverage_dict['class']))

        with open(average_coverage_data_summary_file_path, "a") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(
                [app_name, issue_id_str, average_line_coverage, average_branch_coverage, average_method_coverage,
                 average_class_coverage])
        csv_file.close()


def cluster_testing_result_dirs_by_apk(testing_result_dirs: List[str]):
    clustered_dict: Dict[str, List[str]] = {}
    for tmp_dir in testing_result_dirs:
        target_apk_file_name = get_apk_name(tmp_dir)
        if target_apk_file_name not in clustered_dict:
            clustered_dict[target_apk_file_name] = [tmp_dir]
        else:
            clustered_dict[target_apk_file_name].append(tmp_dir)
    return clustered_dict


def compute_all_run_code_coverage(app_name: str, output_dir, tool_name,
                                  target_app_testing_result_dirs: List[str],
                                  accumulative_coverage_result_file_path):
    clustered_dict = cluster_testing_result_dirs_by_apk(target_app_testing_result_dirs)

    for target_apk_file_name in clustered_dict:

        all_run_testing_result_dirs = clustered_dict[target_apk_file_name]

        coverage_ec_files_str = ""

        for tmp_dir in all_run_testing_result_dirs:

            if tool_name not in tmp_dir:
                # double check to ensure the testing result dir is indeed from the target tool
                continue

            if tool_name == "timemachine":
                coverage_data_dir = os.path.join(tmp_dir, "timemachine-output")
                coverage_ec_files_str += " " + get_coverage_ec_files_str_optimized(coverage_data_dir)
            else:
                coverage_data_dir = tmp_dir
                coverage_ec_files_str += " " + get_coverage_ec_files_str(coverage_data_dir)

        class_files_dirs, source_files_dirs = get_class_source_files_dirs(app_name, target_apk_file_name)

        class_files_dirs_str = get_class_files_str(app_name, class_files_dirs)

        # Assemble and execute the coverage computation command #
        xml_coverage_report_file_path = os.path.join(output_dir, target_apk_file_name + ".coverage_report.xml")
        cmd = "java -jar ../tools/jacococli.jar report " + coverage_ec_files_str + class_files_dirs_str + " --xml " + \
              xml_coverage_report_file_path
        print('$ %s' % cmd)

        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # clear the output
        output = p.communicate()[0].decode('utf-8').strip()
        print(output)

        is_valid_data, line_coverage, branch_coverage, method_coverage, class_coverage = \
            read_coverage_jacoco(xml_coverage_report_file_path)

        # dump info into csv
        if is_valid_data:
            with open(accumulative_coverage_result_file_path, "a") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(
                    [app_name, tool_name, target_apk_file_name, line_coverage, branch_coverage, method_coverage,
                     class_coverage])
            csv_file.close()


def main(args: Namespace):
    # collect all testing result dirs and cluster them according to their app names
    all_testing_results_dirs: Dict[str, List[str]] = {}
    subdirs = os.listdir(args.o)
    for subdir in subdirs:
        # print(subdir)
        subdir_path = os.path.join(args.o, subdir)
        if os.path.isdir(subdir_path):
            app_name = get_app_name(subdir_path)
            if app_name not in all_testing_results_dirs:
                all_testing_results_dirs[app_name] = [subdir_path]
            else:
                all_testing_results_dirs[app_name].append(subdir_path)

    print("---------")
    print(all_testing_results_dirs)
    print("---------")

    if args.timemachine:
        tool_name = "timemachine"
    else:
        if args.monkey:
            tool_name = "monkey"
        elif args.ape:
            tool_name = "ape"
        elif args.combo:
            tool_name = "combodroid"
        elif args.humandroid:
            tool_name = "humandroid"
        elif args.stoat:
            tool_name = "stoat"
        elif args.qtesting:
            tool_name = "qtesting"
        else:
            tool_name = ""

    if args.acc_csv is not None:

        accumulative_coverage_result_file_path = args.acc_csv
        if os.path.exists(accumulative_coverage_result_file_path):
            os.remove(accumulative_coverage_result_file_path)

        for app_name in all_testing_results_dirs:
            # only compute coverage for specific app
            if args.app_name is not None and app_name != args.app_name:
                continue
            target_app_testing_result_dirs = all_testing_results_dirs[app_name]
            # compute coverage for all runs of an apk
            compute_all_run_code_coverage(app_name, args.o, tool_name,
                                          target_app_testing_result_dirs,
                                          accumulative_coverage_result_file_path)

    if args.single_csv is not None:

        single_run_coverage_result_file_path = args.single_csv
        if os.path.exists(single_run_coverage_result_file_path):
            os.remove(single_run_coverage_result_file_path)

        for app_name in all_testing_results_dirs:
            # only compute coverage for specific app
            if args.app_name is not None and app_name != args.app_name:
                continue
            target_app_testing_result_dirs = all_testing_results_dirs[app_name]
            compute_single_run_code_coverage(app_name, tool_name, args.issue_id,
                                             target_app_testing_result_dirs,
                                             single_run_coverage_result_file_path)
    if args.average_csv is not None:

        average_coverage_result_file_path = args.average_csv
        if os.path.exists(average_coverage_result_file_path):
            os.remove(average_coverage_result_file_path)

        for app_name in all_testing_results_dirs:
            # only compute coverage for specific app
            if args.app_name is not None and app_name != args.app_name:
                continue
            target_app_testing_result_dirs = all_testing_results_dirs[app_name]
            compute_average_code_coverage(app_name, tool_name, args.issue_id,
                                          target_app_testing_result_dirs,
                                          average_coverage_result_file_path)


if __name__ == '__main__':

    ap = ArgumentParser()

    ap.add_argument('-o', required=True, help="the output directory of testing results")
    ap.add_argument('-v', default=False, action='store_true')

    # supported fuzzing tools
    ap.add_argument('--monkey', default=False, action='store_true')
    ap.add_argument('--ape', default=False, action='store_true')
    ap.add_argument('--timemachine', default=False, action='store_true')
    ap.add_argument('--combo', default=False, action='store_true')
    ap.add_argument('--humandroid', default=False, action='store_true')
    ap.add_argument('--qtesting', default=False, action='store_true')
    ap.add_argument('--stoat', default=False, action='store_true')

    ap.add_argument('--app', type=str, dest='app_name')
    ap.add_argument('--id', type=str, dest='issue_id')
    ap.add_argument('--acc_csv', type=str, default=None, dest='acc_csv',
                    help="compute the accumulative coverage of all runs")
    ap.add_argument('--single_csv', type=str, default=None, dest='single_csv',
                    help="compute the coverage of single runs")
    ap.add_argument('--average_csv', type=str, default=None, dest='average_csv',
                    help="compute the average coverage of all runs")

    args = ap.parse_args()

    if not os.path.exists(args.o):
        ap.error("Error: the output directory does not exist!")

    main(args)