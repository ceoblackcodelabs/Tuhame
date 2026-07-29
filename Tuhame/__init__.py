try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    # mysqlclient (or no MySQL usage at all, e.g. local SQLite) — fine either way.
    pass
