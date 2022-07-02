# kugenuma

PostgreSQL で TPC-H を動かす実験。

## 環境

- CentOS Linux 7

## 使用したソフトウェア

- [TPC-H Tools v3.0.0](https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp)
- [PostgreSQL 14](https://www.postgresql.org/)
- [tpch-patches](https://github.com/itiut/tpch-patches)
  - TPC-H を PostgreSQL で動かすためのパッチ。一部参考にした。
- [pg_bulkload](https://github.com/ossc-db/pg_bulkload)
  - dbgen で生成したデータを高速に読み込む。

## TPC-H の変更箇所

- dbgen/queries/*.sql
  - PostgreSQL の文法に修正
- dbgen/config.h
  - `EOL_HANDLING` を有効化
- dbgen/dss.ri
  - PostgreSQL の文法に修正
- dbgen/makefile.suite
  - `CC`, `DATABASE`, `MACHINE`, `WORKLOAD`, `LDFLAGS` を設定
- dbgen/tpcd.h
  - `POSTGRES` の設定
