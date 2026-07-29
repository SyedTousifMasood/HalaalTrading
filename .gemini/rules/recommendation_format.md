# RULE: Mandatory Recommendation Format

## Overview
This rule enforces a strict, structured layout for all swing trading stock recommendations presented to the user.

## Directives
Whenever suggesting a stock or trade setup, the agent MUST present the recommendation in a clean table containing the following fields:
1.  **Date:** The date of the scan/recommendation.
2.  **Symbol:** The NSE ticker symbol.
3.  **Composite Score:** The HSTS multi-factor composite score (out of 100).
4.  **Target Entry Price:** The suggested buy price.
5.  **Initial Stop-Loss:** The invalidation level.
6.  **Profit Target:** The exit target.
7.  **Risk-to-Reward Ratio:** Formatted as `1:R` (e.g. `1:2.0`).

## Example Format
| Date | Symbol | Composite Score | Target Entry Price | Initial Stop-Loss | Profit Target | Risk-to-Reward Ratio |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| 2026-07-29 | BERGEPAINT | 83.0 / 100 | ₹520.05 | ₹496.20 | ₹568.10 | 1:2.0 |
