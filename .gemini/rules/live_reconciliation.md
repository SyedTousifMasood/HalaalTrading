# RULE: Mandatory Live Zerodha Reconciliation

## Overview
This rule enforces daily checks to align the calculated Available Capital in the HSTS Trading Journal with live cash balances and holdings in the associated Zerodha account, preventing data mismatch.

## Directives
Before performing any of the following:
1. Suggesting fresh trade setups or position sizing.
2. Updating the `Ledger` or `Capital` sheets in the Trading Journal.
3. Reporting available free trading capital.

The agent MUST:
1. Connect to the Zerodha adapter and fetch live margins (`cash` balance) and holdings.
2. Recalculate available capital in the Excel journal using:
   `deposits + realized_pnl - deployed`
3. Cross-reference the live Zerodha holdings against `OPEN` positions in the Ledger.
4. Identify any mismatches (e.g. unrecorded brokerages, untracked purchases) and log adjustments to reconcile the cash balances to 100% alignment before proceeding.
