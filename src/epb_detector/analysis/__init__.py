"""Statistical analyses on top of model predictions.

Functions here all assume:

- A predictions parquet with at minimum ``window_start, sta, sat,
  epb_probability, label, storm_id, storm_phase, hours_from_dst_min,
  storm_class, dst, kp, ap, F107obs, local_time_mean, ipp_lon_mean``.
- A storm catalogue parquet with ``storm_id, dst_min_time, dst_min_value,
  storm_class, lt_bin, season, recovery_duration_hours,
  solar_cycle_phase, is_intense_or_stronger`` (built by
  :mod:`epb_detector.external.storms.enrich_storm_catalog`).

Bootstrap is *always* by ``storm_id`` for storm-side observations and by
``(sta, day)`` for the quiet-side observations — this corrects for
pseudoreplication that single-window bootstraps would introduce.
"""
