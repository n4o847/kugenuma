#!/usr/bin/env python3

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time

config = {
    "use_pg_hint_plan": True,
}

def parse_sf(sf: str):
    if not re.match(r"^(0|[1-9][0-9]*)(\.[0-9]*[1-9])?$", sf):
        raise Exception(f"invalid scale factor {repr(sf)}")
    safe_sf = re.sub(r"\.", "_", sf)
    logging.info(f"parse {sf} -> {safe_sf}")
    return safe_sf

# データベース作成
def handle_createdb(args: argparse.Namespace):
    logging.info("handle_createdb")
    safe_sf = parse_sf(args.s)
    database = f"sf{safe_sf}"
    subprocess.run(["createdb", database], check=True)

# スキーマ構成
def handle_ddl(args: argparse.Namespace):
    logging.info("handle_ddl")
    safe_sf = parse_sf(args.s)
    database = f"sf{safe_sf}"
    subprocess.run(["psql", "-d", database, "-f", "dss.ddl"], check=True)

# データを生成
def handle_dbgen(args: argparse.Namespace):
    logging.info("handle_dbgen")
    safe_sf = parse_sf(args.s)
    directory = f"tables_sf{safe_sf}"
    os.makedirs(directory, exist_ok=True)
    subprocess.run(["../dbgen", "-f", "-s", args.s, "-b", "../dists.dss"], cwd=directory)
    if False:
        # 末尾の "|" は不要なため削除する
        # EOL_HANDLING を #define してビルドした場合は不要
        for table_file in os.listdir(directory):
            assert table_file.endswith(".tbl")
            logging.info(f"fix {table_file}")
            subprocess.run(["sed", "-i", "-e", "s/|$//", table_file], cwd=directory)

# データをロード
def handle_load(args: argparse.Namespace):
    logging.info("handle_load")
    safe_sf = parse_sf(args.s)
    directory = f"tables_sf{safe_sf}"
    database = f"sf{safe_sf}"
    subprocess.run(["psql", "-d", database, "-c", "CREATE EXTENSION pg_bulkload;"])
    if config["use_pg_hint_plan"]:
        subprocess.run(["psql", "-d", database, "-c", "CREATE EXTENSION pg_hint_plan;"])
    for table_file in os.listdir(directory):
        assert table_file.endswith(".tbl")
        table = re.sub(r"\.tbl$", "", table_file)
        logging.info(f"load {table_file}")
        if False:
            # copy を使う場合
            with open(f"{directory}/{table_file}") as f:
                subprocess.run([
                    "psql", "-d", database, "-c", f"copy {table} from STDIN (delimiter '|');"
                ], cwd=directory, stdin=f, check=True)
        else:
            # pg_bulkload を使う場合 (こちらのほうが速い)
            subprocess.run([
                "/usr/pgsql-14/bin/pg_bulkload",
                "-d", database,
                "-i", table_file,
                "-O", table,
                "-o", "DELIMITER=|",
            ], cwd=directory, check=True)

# インデックスを貼る
def handle_ri(args: argparse.Namespace):
    logging.info("handle_ri")
    safe_sf = parse_sf(args.s)
    database = f"sf{safe_sf}"
    subprocess.run(["psql", "-d", database, "-f", "dss.ri"], check=True)

# クエリを生成
def handle_qgen(args: argparse.Namespace):
    logging.info("handle_qgen")
    safe_sf = parse_sf(args.s)
    directory = f"queries_sf{safe_sf}"
    os.makedirs(directory, exist_ok=True)
    for i in range(1, 10 + 1):
        logging.info(f"generate query {i}")
        query = subprocess.check_output([
            "../qgen",
            "-d",  # デフォルト
            "-x",  # explain
            "-s", args.s,
            "-b", "../dists.dss",
            f"{i}",
        ], cwd="queries").decode()
        if False:
            # tpcd.h を PostgreSQL 用に設定済みであれば不要
            query = re.sub(r"^(where rownum .*)$", r"-- \1", query, flags=re.MULTILINE)
            query = re.sub(r"^(select)$", r"explain analyze \1", query, flags=re.MULTILINE)
        with open(f"{directory}/{i}.sql", mode="w") as f:
            f.write(query)

def cold_start():
    logging.info("purge RAID controller cache")
    subprocess.run(["sudo", "dd", "if=/dev/zero", "of=/export/data1/kusodeka.dat", "bs=1G", "count=16"], check=True)
    logging.info("purge page cache")
    subprocess.run(["sync"], check=True)
    subprocess.run(["sudo", "sysctl", "-w", "vm.drop_caches=3"], check=True)
    logging.info("restart postgresql")
    subprocess.run(["sudo", "systemctl", "restart", "postgresql-14"], check=True)

# 計測
def handle_time(args: argparse.Namespace):
    logging.info("handle_time")
    safe_sf = parse_sf(args.s)
    database = f"sf{safe_sf}"
    directory = f"queries_sf{safe_sf}"
    result_dir = f"results_sf{safe_sf}"
    os.makedirs(result_dir, exist_ok=True)
    result = {}
    for i in range(1, 10 + 1):
        cold_start()
        logging.info(f"execute query {i}")
        result[i] = {}
        query_plan = subprocess.check_output([
            "psql", "-d", database, "-f", f"{directory}/{i}.sql"
        ]).decode()
        execution_time = re.search(r"Execution Time: (.*)", query_plan, flags=re.MULTILINE).group(1)
        logging.info(f"execution time: {execution_time}")
        result[i]["execution_time"] = execution_time
        with open(f"{result_dir}/{i}.txt", mode="w") as f:
            f.write(query_plan)
    print(result, file=sys.stderr)

class SarAnalyzer:
    def __init__(self, dir: str) -> None:
        self.dir = dir

    def start(self):
        os.makedirs(self.dir, exist_ok=True)
        self.outfile_u = open(f"{self.dir}/sar_u.txt", "w")
        self.process_u = subprocess.Popen(["sar", "-u", "1"], stdout=self.outfile_u)
        self.outfile_b = open(f"{self.dir}/sar_b.txt", "w")
        self.process_b = subprocess.Popen(["sar", "-b", "1"], stdout=self.outfile_b)

    def end(self):
        self.process_u.terminate()
        self.process_b.terminate()
        self.outfile_u.close()
        self.outfile_b.close()

    def get_result(self):
        users = []
        breads = []
        bwrtns = []
        with open(f"{self.dir}/sar_u.txt") as f:
            for line in f:
                m = re.match(r"(\d\d:\d\d:\d\d)\s+all\s+([0-9.]+)", line)
                if m is None:
                    continue
                time = m.group(1)
                user = m.group(2)
                users.append((time, user))
        with open(f"{self.dir}/sar_b.txt") as f:
            for line in f:
                m = re.match(r"(\d\d:\d\d:\d\d)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)", line)
                if m is None:
                    continue
                time = m.group(1)
                bread = m.group(5)
                bwrtn = m.group(6)
                breads.append((time, bread))
                bwrtns.append((time, bwrtn))
        return users, breads, bwrtns

class SelfMadeAnalyzer:
    def start(self):
        self.process = subprocess.Popen(["../perf/target/release/perf"], stdout=subprocess.PIPE)

    def end(self):
        self.process.terminate()
        self.result = ''.join([line.decode() for line in self.process.stdout.readlines()])

    def save_result(self, dir: str):
        pass

    def get_result(self):
        users = []
        breads = []
        bwrtns = []
        for i, line in enumerate(self.result.splitlines()):
            if i == 0:
                continue
            time, _, bread, _, bwrtn, user, *_ = map(int, line.split())
            time //= 1000
            time = f"{time // 3600 :02}:{time // 60 % 60 :02}:{time % 60 :02}"
            user = f"{user}.00"
            bread = f"{bread}.00"
            bwrtn = f"{bwrtn}.00"
            users.append((time, user))
            breads.append((time, bread))
            bwrtns.append((time, bwrtn))
        return users, breads, bwrtns

# CPU 利用率とディスク I/O の解析
def handle_analyze(args: argparse.Namespace):
    logging.info("handle_analyze")
    safe_sf = parse_sf(args.s)

    database = f"sf{safe_sf}"
    directory = f"queries_sf{safe_sf}"
    result_dir = f"results_sf{safe_sf}"
    os.makedirs(result_dir, exist_ok=True)

    queries = list(map(int, args.q.split(",")))

    result = {}

    for i in queries:
        analyzer = SarAnalyzer(dir=f"{result_dir}/{i}")
        cold_start()
        logging.info(f"execute query {i}")
        analyzer.start()
        time.sleep(2)
        result[i] = {}
        query_plan = subprocess.check_output([
            "psql", "-d", database, "-f", f"{directory}/{i}.sql"
        ]).decode()
        time.sleep(2)
        analyzer.end()
        execution_time = re.search(r"Execution Time: (.*)", query_plan, flags=re.MULTILINE).group(1)
        logging.info(f"execution time: {execution_time}")
        result[i]["execution_time"] = execution_time
        with open(f"{result_dir}/{i}.txt", mode="w") as f:
            f.write(query_plan)
        users, breads, bwrtns = analyzer.get_result()
        result[i]["users"] = dict(users)
        result[i]["breads"] = dict(breads)
        result[i]["bwrtns"] = dict(bwrtns)
        print(json.dumps(result[i]), file=sys.stderr)
    with open(f"{result_dir}/all.json", mode="w") as f:
        json.dump(result, f, indent=4)
    print(json.dumps(result), file=sys.stderr)

# 一連の流れを全部やる
def handle_all(args: argparse.Namespace):
    logging.info("handle_all")
    handle_createdb(args)
    handle_ddl(args)
    if not args.p: handle_dbgen(args)
    handle_load(args)
    handle_ri(args)
    if not args.p: handle_qgen(args)
    handle_analyze(args)

def main():
    # sys.tracebacklimit = 0
    os.environ["LANG"] = "C.UTF-8"
    logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO, datefmt="%H:%M:%S")

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_createdb = subparsers.add_parser("createdb")
    parser_createdb.add_argument('-s', required=True, help="scale factor")
    parser_createdb.set_defaults(handler=handle_createdb)

    parser_ddl = subparsers.add_parser("ddl")
    parser_ddl.add_argument('-s', required=True, help="scale factor")
    parser_ddl.set_defaults(handler=handle_ddl)

    parser_dbgen = subparsers.add_parser("dbgen")
    parser_dbgen.add_argument('-s', required=True, help="scale factor")
    parser_dbgen.set_defaults(handler=handle_dbgen)

    parser_load = subparsers.add_parser("load")
    parser_load.add_argument('-s', required=True, help="scale factor")
    parser_load.set_defaults(handler=handle_load)

    parser_ri = subparsers.add_parser("ri")
    parser_ri.add_argument('-s', required=True, help="scale factor")
    parser_ri.set_defaults(handler=handle_ri)

    parser_qgen = subparsers.add_parser("qgen")
    parser_qgen.add_argument('-s', required=True, help="scale factor")
    parser_qgen.set_defaults(handler=handle_qgen)

    parser_time = subparsers.add_parser("time")
    parser_time.add_argument('-s', required=True, help="scale factor")
    parser_time.set_defaults(handler=handle_time)

    parser_analyze = subparsers.add_parser("analyze")
    parser_analyze.add_argument('-s', required=True, help="scale factor")
    parser_analyze.add_argument('-q', default='1,2,3,4,5,6,7,8,9,10', help="queries to execute (separated by commas)")
    parser_analyze.set_defaults(handler=handle_analyze)

    parser_all = subparsers.add_parser("all")
    parser_all.add_argument('-s', required=True, help="scale factor")
    parser_all.add_argument('-p', action="store_true", help="dbgen and qgen are already done")
    parser_all.set_defaults(handler=handle_all)

    args = parser.parse_args()
    if hasattr(args, "handler"):
        args.handler(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
