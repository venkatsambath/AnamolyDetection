"""
Constants from the Kaggle notebook — preserved verbatim.
GAUGE_METRICS, METRIC_COLUMNS_AVGTIME, METRIC_REASONS_AVGTIME.
"""

GAUGE_METRICS = [
    'GetGroupsAvgTime', 'ThreadsBlocked', 'ThreadsWaiting', 'ThreadsTimedWaiting',
    'GcTimeMillisParNew', 'GcTimeMillisConcurrentMarkSweep', 'CallQueueLength',
    'RpcProcessingTimeAvgTime', 'RpcQueueTimeAvgTime', 'CreateAvgTime',
    'MkdirsAvgTime', 'DeleteAvgTime', 'RenameAvgTime', 'Rename2AvgTime',
    'CompleteAvgTime', 'GetFileInfoAvgTime', 'GetBlockLocationsAvgTime',
    'GetListingAvgTime', 'GetContentSummaryAvgTime', 'FsyncAvgTime',
    'ConcatAvgTime', 'CreateSnapshotAvgTime', 'DeleteSnapshotAvgTime',
    'RenameSnapshotAvgTime', 'GetSnapshotDiffReportAvgTime',
    'GetSnapshotDiffReportListingAvgTime', 'GetDatanodeReportAvgTime',
    'GetDatanodeStorageReportAvgTime',
]

METRIC_COLUMNS_AVGTIME = [
    'GetGroupsAvgTime', 'ThreadsBlocked', 'ThreadsWaiting', 'ThreadsTimedWaiting',
    'GcTimeMillisParNew', 'GcTimeMillisConcurrentMarkSweep', 'CallQueueLength',
    'RpcProcessingTimeAvgTime', 'RpcQueueTimeAvgTime',
    'CreateAvgTime', 'MkdirsAvgTime', 'DeleteAvgTime', 'RenameAvgTime',
    'Rename2AvgTime', 'CompleteAvgTime', 'GetFileInfoAvgTime', 'GetBlockLocationsAvgTime',
    'GetListingAvgTime', 'GetContentSummaryAvgTime', 'FsyncAvgTime', 'ConcatAvgTime',
    'CreateSnapshotAvgTime', 'DeleteSnapshotAvgTime', 'RenameSnapshotAvgTime',
    'GetSnapshotDiffReportAvgTime', 'GetSnapshotDiffReportListingAvgTime',
    'GetDatanodeReportAvgTime', 'GetDatanodeStorageReportAvgTime',
]

METRIC_REASONS_AVGTIME = {
    'GetGroupsAvgTime': {
        'description': 'Average time for GetGroups operations',
        'high_impact': 'High average time for GetGroups calls, indicating delays in user/service authentication requests.',
        'possible_causes': [
            'Slowness in external authentication systems (LDAP, Kerberos)',
            'NameNode under heavy load, delaying group lookups',
            'Network latency to authentication servers',
        ],
    },
    'GcTimeMillisParNew': {
        'description': 'Time spent in ParNew garbage collection (minor GC) per minute',
        'high_impact': 'Frequent or long minor GC pauses occurring in the last minute, indicating high object creation rate.',
        'possible_causes': [
            'High rate of temporary object allocation by applications',
            'Inefficient application code generating garbage rapidly',
            'Insufficient young generation heap size allocated to NameNode JVM',
        ],
    },
    'GcTimeMillisConcurrentMarkSweep': {
        'description': 'Time spent in Concurrent Mark Sweep garbage collection (major GC) per minute',
        'high_impact': 'Frequent or long major GC pauses ("Stop-the-World" events) occurring in the last minute.',
        'possible_causes': [
            'Insufficient NameNode heap memory (-Xmx JVM argument) leading to aggressive major GCs',
            'Memory leaks or excessive long-lived objects holding onto memory',
            'Too many in-memory objects (e.g., many small files in HDFS namespace) putting pressure on old generation heap',
        ],
    },
    'CallQueueLength': {
        'description': 'Length of the RPC call queue',
        'high_impact': 'NameNode is overwhelmed with RPC requests, handlers are saturated.',
        'possible_causes': [
            'High client load (too many file system operations)',
            'Slow RPC processing (CPU/IO bottlenecks)',
            'Insufficient dfs.namenode.handler.count',
            'Network issues affecting client-NN communication',
        ],
    },
    'RpcProcessingTimeAvgTime': {
        'description': 'Average time to process an RPC call',
        'high_impact': 'RPC calls are taking too long to process after being dequeued.',
        'possible_causes': [
            'CPU contention on NameNode (too many threads/processes)',
            'I/O bottlenecks (for metadata operations, e.g., disk for edits log)',
            'Inefficient code paths in NameNode operations',
            'Large number of small files leading to metadata pressure',
        ],
    },
    'RpcQueueTimeAvgTime': {
        'description': 'Average time an RPC call spends in the queue before processing',
        'high_impact': 'RPC calls are spending excessive time waiting in the queue.',
        'possible_causes': [
            'NameNode handler threads are saturated/busy',
            'Sudden spikes in client requests',
            'Slow processing of previous requests leading to backlog',
        ],
    },
    'ThreadsBlocked': {
        'description': 'Number of threads in a blocked state',
        'high_impact': 'Threads are waiting for a monitor lock to enter a synchronized block/method.',
        'possible_causes': [
            'Lock contention within NameNode code',
            'Deadlocks (rare but possible)',
            'Slow I/O operations causing threads to block',
        ],
    },
    'ThreadsWaiting': {
        'description': 'Number of threads in a waiting state (indefinite wait)',
        'high_impact': 'Threads are waiting indefinitely for another thread to perform a particular action.',
        'possible_causes': [
            'Internal synchronization issues',
            'Resource starvation',
            'Waiting on external services',
        ],
    },
    'ThreadsTimedWaiting': {
        'description': 'Number of threads in a timed waiting state (wait for a specified time)',
        'high_impact': 'Threads are waiting for a specified period for an action.',
        'possible_causes': [
            'Expected behavior during certain operations (e.g., polling)',
            'Could indicate delays if timed waits are excessively long or frequent.',
        ],
    },
    'RenameAvgTime': {
        'description': 'Average time for rename operation',
        'high_impact': 'File rename operations are slow.',
        'possible_causes': [
            'High contention on metadata locks',
            'Large directories being renamed',
            "I/O bottlenecks on the NameNode's disk (for edits log)",
        ],
    },
    'DeleteAvgTime': {
        'description': 'Average time for delete operation',
        'high_impact': 'File delete operations are slow.',
        'possible_causes': [
            'Large directories being deleted',
            'High contention on metadata locks',
            "I/O bottlenecks on the NameNode's disk",
        ],
    },
    'CreateAvgTime': {
        'description': 'Average time for create operation',
        'high_impact': 'File creation operations are slow.',
        'possible_causes': [
            'High client load',
            'High contention for namespace locks',
            'Slow journaling (for HA setups)',
        ],
    },
    'GetFileInfoAvgTime': {
        'description': 'Average time for getFileInfo operation',
        'high_impact': 'Retrieving file metadata is slow.',
        'possible_causes': [
            'Too many small files',
            'High contention on metadata locks',
            'I/O bottlenecks',
        ],
    },
    'GetBlockLocationsAvgTime': {
        'description': 'Average time to get block locations for a file',
        'high_impact': 'Retrieving block locations is slow, affecting read performance.',
        'possible_causes': [
            'High client load on NameNode',
            'Network latency between NameNode and DataNodes',
            'Slow Datanode heartbeats/reporting',
            'Large number of blocks in the file',
        ],
    },
    'Rename2AvgTime': {
        'description': 'Time taken to rename (V2)',
        'high_impact': 'Rename (V2) is taking too long.',
        'possible_causes': [
            'This is unusual, rename should not take this long. Check your NameNode audit logs for specifics.',
        ],
    },
    'GetListingAvgTime': {
        'description': 'Time taken for listStatus (ls) operation',
        'high_impact': 'Directory listing (ls) operations are taking too long.',
        'possible_causes': [
            'The directory being listed likely contains too many files or is too deep. Check NameNode audit logs for expensive ls commands.',
        ],
    },
    'GetContentSummaryAvgTime': {
        'description': 'Average time for getContentSummary operation (du equivalent)',
        'high_impact': 'Content summary (du equivalent) is an expensive operation in large directories with many files/sub-directories.',
        'possible_causes': [
            'Check NameNode audit logs to identify which user or application ran an expensive du command on a potentially huge directory.',
        ],
    },
    'CompleteAvgTime': {
        'description': 'Average time for complete operation (happens while closing a file)',
        'high_impact': "CompleteAvgTime should typically not take long. If it is, it's likely a red herring and requires further analysis.",
        'possible_causes': [
            'This metric often appears as a red herring. Focus analysis on other directly impactful metrics first.',
        ],
    },
    'FsyncAvgTime': {
        'description': 'Average time for fsync operation (synchronizing data to disk)',
        'high_impact': 'FsyncAvgTime taking long implies I/O blocking threads.',
        'possible_causes': [
            'Investigate NameNode disk performance and underlying storage I/O bottlenecks.',
        ],
    },
    'ConcatAvgTime': {
        'description': 'Average time for concat operation',
        'high_impact': 'File concatenation operations are slow.',
        'possible_causes': ['High contention on metadata locks during concat'],
    },
    'CreateSnapshotAvgTime': {
        'description': 'Average time for createSnapshot operation',
        'high_impact': 'Snapshot creation operations are slow.',
        'possible_causes': ['Large namespace, high metadata load during snapshot creation'],
    },
    'DeleteSnapshotAvgTime': {
        'description': 'Average time for deleteSnapshot operation',
        'high_impact': 'Snapshot deletion operations are slow.',
        'possible_causes': ['Large number of changes in snapshot, high metadata load during deletion'],
    },
    'RenameSnapshotAvgTime': {
        'description': 'Average time for renameSnapshot operation',
        'high_impact': 'Snapshot rename operations are slow.',
        'possible_causes': ['Metadata contention'],
    },
    'GetSnapshotDiffReportAvgTime': {
        'description': 'Average time for getSnapshotDiffReport operation',
        'high_impact': 'Generating snapshot diff reports is very slow and resource-intensive.',
        'possible_causes': ['Very large number of changes between snapshots', 'NameNode under heavy load'],
    },
    'GetSnapshotDiffReportListingAvgTime': {
        'description': 'Average time for getSnapshotDiffReportListing operation',
        'high_impact': 'Listing snapshot diff reports is slow.',
        'possible_causes': ['Large number of diffs, similar to GetSnapshotDiffReportAvgTime'],
    },
    'GetDatanodeReportAvgTime': {
        'description': 'Average time for getDatanodeReport operation',
        'high_impact': 'GetDatanodeReportAvgTime taking long suggests potential network issues.',
        'possible_causes': [
            'Check network connectivity and latency between the NameNode and DataNodes.',
        ],
    },
    'GetDatanodeStorageReportAvgTime': {
        'description': 'Average time for getDatanodeStorageReport operation',
        'high_impact': 'Retrieving DataNode storage reports is slow.',
        'possible_causes': ['Many DataNodes, network latency, DataNodes slow to respond.'],
    },
    'MkdirsAvgTime': {
        'description': 'Average time for mkdirs operation',
        'high_impact': 'Directory creation operations are slow.',
        'possible_causes': ['High contention on namespace locks', 'Slow journaling'],
    },
}
