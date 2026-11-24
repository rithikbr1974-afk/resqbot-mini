// Survivor detection: finds a body-temperature blob in a thermal sweep and scores confidence.
// Plain C++ (no Arduino calls) so the same logic is mirrored and tested in sim/detection.py.
#pragma once
#include <math.h>
#include <string.h>
#include "config.h"

struct Finding {
  bool found = false;        // a person-like warm blob
  bool fire = false;         // a cell hotter than FIRE_C
  float background = NAN;    // median of the sweep, degC
  float peak = NAN;          // warmest body-range cell, degC
  float delta = 0;           // peak - background
  int cells = 0;             // cells in the blob
  float panAngle = PAN_CENTER;  // servo angle of the blob centre (90 = straight ahead)
  float hottest = NAN;       // hottest cell of all (for the fire warning)
  int row = 0;               // tilt row of the peak
};

// Median of up to 64 values, NANs skipped.
inline float medianOf(const float *v, int n) {
  float tmp[64]; int k = 0;
  for (int i = 0; i < n && k < 64; i++) if (!isnan(v[i])) tmp[k++] = v[i];
  if (k == 0) return NAN;
  for (int i = 1; i < k; i++) {        // insertion sort, n is tiny
    float x = tmp[i]; int j = i - 1;
    while (j >= 0 && tmp[j] > x) { tmp[j + 1] = tmp[j]; j--; }
    tmp[j + 1] = x;
  }
  return k % 2 ? tmp[k / 2] : (tmp[k / 2 - 1] + tmp[k / 2]) / 2;
}

// grid is rows x cols, row-major. Column c is at servo angle PAN_MIN + c * PAN_STEP.
inline Finding analyzeSweep(const float *grid, int rows, int cols) {
  Finding f;
  f.background = medianOf(grid, rows * cols);
  if (isnan(f.background)) return f;

  // 1. which cells look like a body: clearly warmer than the scene, but not hotter than a person
  bool warmCol[32] = {false};
  float colDelta[32] = {0};
  int colCells[32] = {0};
  int colRow[32] = {0};
  for (int r = 0; r < rows; r++)
    for (int c = 0; c < cols && c < 32; c++) {
      float t = grid[r * cols + c];
      if (isnan(t)) continue;
      if (isnan(f.hottest) || t > f.hottest) f.hottest = t;
      float d = t - f.background;
      if (d >= DELTA_MIN_C && t <= BODY_MAX_C) {
        warmCol[c] = true;
        colCells[c]++;
        if (d > colDelta[c]) { colDelta[c] = d; colRow[c] = r; }
      }
    }
  f.fire = !isnan(f.hottest) && f.hottest >= FIRE_C;

  // 2. the largest run of neighbouring warm columns is the candidate
  int bestStart = -1, bestLen = 0, bestCells = 0;
  for (int c = 0; c < cols && c < 32;) {
    if (!warmCol[c]) { c++; continue; }
    int s = c, cells = 0;
    while (c < cols && c < 32 && warmCol[c]) cells += colCells[c++];
    int len = c - s;
    if (cells > bestCells || (cells == bestCells && len > bestLen)) { bestStart = s; bestLen = len; bestCells = cells; }
  }
  if (bestStart < 0 || bestCells < MIN_BLOB_CELLS) return f;

  // 3. centre = delta-weighted average angle; peak = warmest column of the blob
  float wsum = 0, asum = 0, best = 0;
  for (int c = bestStart; c < bestStart + bestLen; c++) {
    wsum += colDelta[c];
    asum += colDelta[c] * (PAN_MIN + c * PAN_STEP);
    if (colDelta[c] > best) { best = colDelta[c]; f.row = colRow[c]; }
  }
  f.found = true;
  f.cells = bestCells;
  f.delta = best;
  f.peak = f.background + best;
  f.panAngle = asum / wsum;
  return f;
}

// Confidence 0-100 from four independent clues.
//  thermal: how much warmer than the background (20-40)
//  size:    how many cells the warm area covers (0-10)
//  rise:    reading got warmer as the robot drove closer, so it is a real heat source (0 or 25)
//  motion:  PIR saw movement while the robot stood still (0 or 25)
inline int confidenceScore(const Finding &f, float closeReading, bool motion) {
  if (!f.found) return 0;
  float thermal = 20 + fminf(20.0f, (f.delta - DELTA_MIN_C) * 8.0f);
  float size = fminf(10.0f, (f.cells - 1) * 5.0f);
  bool rise = !isnan(closeReading) && closeReading - f.peak >= 0.5f && closeReading <= BODY_MAX_C;
  int score = (int)(thermal + size + (rise ? 25 : 0) + (motion ? 25 : 0));
  return score > 100 ? 100 : score;
}
