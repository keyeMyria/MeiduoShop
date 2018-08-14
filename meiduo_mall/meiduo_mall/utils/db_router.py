class MasterSlaveDBRouter(object):
    """数据库主从读写分离路由"""

    # note--数据库查询时候执行该方法
    def db_for_read(self, model, **hints):
        """读数据库"""
        # 表示查询哪个model的数据, 然后发送给哪个数据库执行
        return "slave"

    # note--写的时候执行该方法
    def db_for_write(self, model, **hints):
        """写数据库"""
        return "default"

    # select * from xx inner join　关联查询
    def allow_relation(self, obj1, obj2, **hints):
        """是否运行关联操作"""
        return True