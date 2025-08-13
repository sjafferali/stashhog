# Registry of all available daemon classes
# Import is deferred to avoid circular imports
def get_daemon_classes():
    from app.daemons.auto_plan_applier_daemon import AutoPlanApplierDaemon
    from app.daemons.auto_video_analysis_daemon import AutoVideoAnalysisDaemon
    from app.daemons.test_daemon import TestDaemon
    from app.models.daemon import DaemonType

    return {
        DaemonType.TEST_DAEMON: TestDaemon,
        DaemonType.AUTO_VIDEO_ANALYSIS_DAEMON: AutoVideoAnalysisDaemon,
        DaemonType.AUTO_PLAN_APPLIER_DAEMON: AutoPlanApplierDaemon,
    }


__all__ = ["get_daemon_classes"]
