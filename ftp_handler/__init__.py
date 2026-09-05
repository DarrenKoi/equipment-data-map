"""Equipment FTP fleet collection, organized by purpose.

Copied from ``skewnono_v3_nuxt``. Three subpackages, each a re-export hub so
call sites import the leaf name:

  - ``core``              — shared primitives: ``FtpClient`` (one server, the
                            ad-hoc list/download/upload/remove ops) and the NLST
                            normalizer both downloaders share. Stdlib only.
  - ``direct_downloader`` — talk to the FTP servers directly: ``FtpFleetDownloader``
                            (concurrent fan-out + ``list_dirs`` discovery) and the
                            archive→parse→index glue (``collect_fleet``). Stdlib only.
  - ``proxy``             — the firewalled-client HTTP transport. The client
                            (``proxy_downloader``) re-exports a ``FtpFleetDownloader``
                            with the SAME surface as ``direct_downloader``. The server
                            (``proxy.flask_proxy``) is imported explicitly so the
                            client never drags in ``flask``.

Which transport a machine gets is a platform fact, not a call-site choice, so
ask ``fleet_downloader()`` rather than picking an import by hand::

    from ftp_handler import fleet_downloader
    dl = fleet_downloader()(hosts, ...)      # proxy on Windows, direct elsewhere

The upstream ``web_app`` subpackage (``BackgroundJobs``, apscheduler) was left
behind — this rollout has no web request thread to get off.

MinIO and pandas sinks take an injected client and are never imported here, so
``core`` and ``direct_downloader`` stay stdlib-only; only ``proxy`` adds a
dependency (``requests`` on the client, ``flask`` on the server).
"""

import os
import sys


def fleet_downloader(platform: str = sys.platform):
    """Return the ``FtpFleetDownloader`` class this machine can actually use.

    The engineer PCs are Windows and have no FTP egress, so they route through
    the proxy; Linux hosts (the proxy host itself, an Airflow worker) reach the
    equipment directly. Both classes expose the same surface, so the transport
    is the only thing that differs.

    ``FTP_TRANSPORT=direct|proxy`` overrides the platform guess — the mapping is
    about where the firewall sits, not about the OS, and a machine can sit on
    the wrong side of it.

    The import is lazy on purpose: the direct path never loads ``requests``.
    """
    transport = os.environ.get("FTP_TRANSPORT") or (
        "proxy" if platform.startswith("win") else "direct"
    )
    if transport == "proxy":
        from .proxy import FtpFleetDownloader
    elif transport == "direct":
        from .direct_downloader import FtpFleetDownloader
    else:
        raise ValueError(
            f"FTP_TRANSPORT must be 'direct' or 'proxy', got {transport!r}"
        )
    return FtpFleetDownloader


__all__ = ["fleet_downloader"]
