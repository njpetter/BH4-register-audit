# BH-4 Visitor & Maintenance Register — Research Notes

## Context
- **Who this is for:** Satyajit Mishra, Security Guard, Boys Hostel 4 (BH-4), IIIT Allahabad
- **Date:** Nov 20, 2026

## Problem
1. At the BH-4 guard desk, one paper register mixes IIITA maintenance workers (cooler, AC, electrician, carpenter) with regular visitors.
2. Entries are handwritten in mixed Hindi and English, and dates are written inconsistently from page to page.
3. People arriving in groups are often noted only as "+1" or "+2" instead of separate rows.
4. Exit times are frequently missing because people leave without signing out at the desk.
5. Whenever someone asks when the cooler guy last came or if anyone forgot to sign out, Satyajit has to flip through pages manually.

## Existing Solutions & Why They Don't Work Here

### 1. Commercial Visitor Management Apps (e.g., MyGate, Veris)
- **What they do:** Paid mobile/tablet apps built for gated societies and offices to log visitors digitally, notify residents/hosts for approval, and keep searchable entry logs.
- **Why they don't work at BH-4:** The BH-4 guard desk only has a landline phone and paper registers—no dedicated tablet, Wi-Fi setup, or institute-wide app for students and maintenance staff. They also require paid subscriptions and institutional rollout, slow down the gate if a guard has to type every walk-in on a phone, and do not help extract or audit records already written in the mandatory paper register.

### 2. Manual Google Forms or Excel Spreadsheets
- **What they do:** Free digital forms or spreadsheets where visitor details are typed in manually so rows can be filtered or searched later.
- **Why they don't work at BH-4:** There is no computer at the guard desk for live entry, so someone would have to manually type up mixed Hindi/English handwritten pages afterward, which is slow and error-prone. Without strict data entry, free-text typing still produces inconsistent dates, spelling variations, and group notes like "+1/+2", leaving the same manual cleanup work just to check missing sign-outs or past maintenance visits.

## Sources

### 1. Nodeflux — AI Visitor Management System
- **Link:** https://www.nodeflux.ai/blog/ai-visitor-management-system/
- **My Notes (3 lines):**
  1. Reading this blog i understood why Logbooks are a serious security risk with one main concern that is there is no searchable audit trail. And manually checking is prone to human errors and extremely time consuming.
  2. An AI visitor management setup on the other hand uses proper pre registration, facial recognition and automated alerts there by making it far more effective than traditional paper based logging!
  3. This problem exactly mirrors the issue with current BH4 paper logging. Which is why i am trying to build a small script to sort and audit these entries and make it more efficient and reliable.

### 2. MyGate — Visitor Management
- **Link:** https://mygate.com/blog/feature-in-focus/visitor-management/
- **My Notes (3 lines):**
  1. This replaces the paper audit with proper digital footprint of visits which is more reliable.
  2. Both guard and resident have connected apps which help in proper digital auditing.
  3. The ERP app could be used for this purpose but is currently out of the scope of current project!
