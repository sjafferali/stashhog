# Registry of all available daemon classes
# Import is deferred to avoid circular imports
def get_daemon_classes():
    from app.daemons.auto_plan_applier_daemon import AutoPlanApplierDaemon
    from app.daemons.auto_stash_sync_daemon import AutoStashSyncDaemon
    from app.daemons.auto_video_analysis_daemon import AutoVideoAnalysisDaemon
    from app.daemons.download_processor_daemon import DownloadProcessorDaemon
    from app.daemons.test_daemon import TestDaemon
    from app.models.daemon import DaemonType

    return {
        DaemonType.TEST_DAEMON: TestDaemon,
        DaemonType.AUTO_VIDEO_ANALYSIS_DAEMON: AutoVideoAnalysisDaemon,
        DaemonType.AUTO_PLAN_APPLIER_DAEMON: AutoPlanApplierDaemon,
        DaemonType.AUTO_STASH_SYNC_DAEMON: AutoStashSyncDaemon,
        DaemonType.DOWNLOAD_PROCESSOR_DAEMON: DownloadProcessorDaemon,
    }


__all__ = ["get_daemon_classes"]
