# 🌐 Client Web Infrastructure & Access Onboarding FAQ
### A Step-by-Step Technical Guide for Web Developers & Designers

---

## 📑 Table of Contents
1. [Prompt Contract & Methodology](#prompt-contract--methodology)
2. [Phase 0: "I Have No Idea Who Hosts Me" – 3-Minute Discovery Triage](#phase-0-i-have-no-idea-who-hosts-me--3-minute-discovery-triage)
3. [The Golden Rule: Delegated Access vs. Password Sharing](#the-golden-rule-delegated-access-vs-password-sharing)
4. [Step-by-Step Access Guides for Top 10 Platforms](#step-by-step-access-guides-for-top-10-platforms)
   - [1. GoDaddy](#1-godaddy)
   - [2. Hostinger](#2-hostinger)
   - [3. Shopify](#3-shopify)
   - [4. Wix](#4-wix)
   - [5. Squarespace](#5-squarespace)
   - [6. WordPress.com & WP Admin](#6-wordpresscom--wp-admin)
   - [7. SiteGround](#7-siteground)
   - [8. Bluehost (Newfold Digital)](#8-bluehost-newfold-digital)
   - [9. WP Engine](#9-wp-engine)
   - [10. Namecheap & Generic cPanel](#10-namecheap--generic-cpanel)
5. [Reverse Prompt Toolkit: Copy-Paste Client Scripts](#reverse-prompt-toolkit-copy-paste-client-scripts)
6. [Emergency Escalations & Common Roadblocks](#emergency-escalations--common-roadblocks)

---

## 📜 Prompt Contract & Methodology

| Element | Specification |
| :--- | :--- |
| **User Role** | Professional Web Developer & Designer |
| **Target Audience** | Non-technical or semi-technical small/medium business owners, marketing managers, and clients |
| **Objective** | Seamlessly extract hosting identity, admin console access, DNS delegation, and CMS credentials without friction or security hazards |
| **Prompt Architecture** | **Prompt Contract** (formal scope & deliverables) + **Reverse Prompts** (client inquiry templates & diagnostic trees) + **Iceberg Context** (structured deep documentation on disk with actionable executive summaries) |
| **Security Standard** | Principle of Least Privilege; prioritize official Delegate/Collaborator invites over sharing master account passwords or 2FA tokens |

---

## 🕵️ Phase 0: "I Have No Idea Who Hosts Me" – 3-Minute Discovery Triage

When a customer says, *"I just pay someone and have no clue where the website lives,"* follow this rapid 3-step triage before asking them to dig through paper files.

### Step 1: Run the Automated Hosting Detector Agent
In your workspace terminal, run your local detection agent:
```bash
python hosting_detector_agent.py "clientwebsite.com" -v
```
This instantly inspects DNS-over-HTTPS (NS, CNAME, SOA), HTTP headers, reverse DNS (PTR), and IP ASN. In 3 seconds, it gives you the exact hosting provider (e.g., Hostinger, GoDaddy, Shopify, Squarespace).

### Step 2: The 60-Second Email & Credit Card Search
Ask the client to open their accounting software (QuickBooks, Xero) or email inbox and search for these recurring billing terms:
- `GoDaddy` / `Domain Control`
- `Hostinger`
- `Shopify`
- `Squarespace`
- `Wix.com`
- `Bluehost` / `Newfold Digital` / `Endurance`
- `SiteGround`
- `WP Engine`
- `Automattic` / `WordPress`
- `Namecheap`
- `Google Domains` / `Squarespace Domains`
- `Cloudflare`

### Step 3: Domain vs. Hosting Disambiguation
Explain this simple analogy to the client:
- **Domain Name (Registrar)** = The street address (e.g., `www.yourbusiness.com`).
- **Web Hosting** = The physical house and land where your website files live.
- **DNS (Domain Name System)** = The road sign pointing the address to the house.
- **CMS (Content Management System)** = The furniture and interior decor (e.g., WordPress, Shopify).

---

## 🔐 The Golden Rule: Delegated Access vs. Password Sharing

> [!IMPORTANT]
> **Never ask clients to email or text you their personal master username and password.**
> 1. It exposes their payment cards, personal billing information, and email accounts.
> 2. It triggers 2-Factor Authentication (2FA) SMS locks every time you try to log in from a new IP or browser.
> 3. Modern platforms have official **Delegate Access / Collaborator** features where the client invites your developer email address.

If direct credentials are unavoidable (e.g., legacy cPanel or raw FTP), mandate an encrypted handoff tool such as:
- **Bitwarden Send** (Free, encrypted, password-protected, auto-expires)
- **1Password Share**
- **Privnote** (One-time self-destructing link)

---

## 🛠️ Step-by-Step Access Guides for Top 10 Platforms

---

### 1. GoDaddy

#### How the Client Identifies It:
- Billing from "GoDaddy.com".
- Nameservers usually contain `domaincontrol.com`.

#### What the Developer Needs:
- **Delegate Access** with permissions to manage products, domains, and DNS.

#### Step-by-Step Instructions for the Client:
1. Log in to [GoDaddy Account Settings](https://account.godaddy.com/).
2. Click your name in the top right corner and select **Account Settings** -> **Delegate Access**.
3. Under the **People who can access my account** section, click **Invite to Access**.
4. Enter the Developer’s:
   - **Name**: `[Your Name / Agency Name]`
   - **Email**: `[Your Developer Email]`
5. Under **Access Level**, select:
   - **Products & Domains** (allows managing websites, hosting, and DNS without exposing credit cards or billing).
6. Click **Invite**.
7. *Notify Developer*: "An invitation email has been sent."

---

### 2. Hostinger

#### How the Client Identifies It:
- Recurring charge from "Hostinger".
- Emails from `@hostinger.com`.
- Nameservers: `ns1.dns-parking.com` or `*.hostinger.com`.

#### What the Developer Needs:
- Account Sharing / Collaboration access to manage hPanel, File Manager, Databases, and DNS.

#### Step-by-Step Instructions for the Client:
1. Log in to the [Hostinger hPanel](https://hpanel.hostinger.com/).
2. In the top right corner, click your **Profile icon** and select **Account Sharing**.
3. In the **Share Access** tab, click **Grant Access**.
4. Enter the Developer's email address: `[Your Developer Email]`.
5. Under **Services to share**, choose:
   - Either **All current and future services** or select the specific website domain.
6. Check the permissions for:
   - **Manage hosting & websites**
   - **Manage domains & DNS**
7. Click **Grant Access**. The developer will receive an invitation link in their inbox.

---

### 3. Shopify

#### How the Client Identifies It:
- Admin login at `https://admin.shopify.com/store/[store-name]`.
- Credit card charge from "Shopify".

#### What the Developer Needs:
- **Collaborator Request** (Recommended via Shopify Partner Dashboard) OR **Staff Account**.

#### Path A (Recommended: Developer Requests Access via Shopify Partner Dashboard):
1. Developer asks client for their **4-digit Collaborator Request Code** (located in client's `Settings -> Users and permissions -> Collaborator request code`).
2. Developer sends request directly from Partner Dashboard. Client simply clicks **Accept**.

#### Path B (Client manually invites Developer as Staff):
1. Log in to Shopify Admin.
2. Go to bottom left: **Settings** (gear icon) -> **Users and permissions**.
3. In the **Staff** section, click **Add staff**.
4. Enter Developer:
   - **First & Last Name**: `[Your Name]`
   - **Email**: `[Your Developer Email]`
5. Set Permissions:
   - Check **Themes** (essential for design/code edits).
   - Check **Apps**, **Pages**, **Navigation**, **Products**, and **Settings**.
   - Leave financial/payout permissions unchecked.
6. Click **Send invite**.

---

### 4. Wix

#### How the Client Identifies It:
- Website built on Wix editor.
- Monthly or yearly charge from "Wix.com".

#### What the Developer Needs:
- **Website Designer** or **Website Manager** role.

#### Step-by-Step Instructions for the Client:
1. Log in to the [Wix Dashboard](https://manage.wix.com/).
2. In the left-hand sidebar, click **Settings**.
3. Click **Roles & Permissions** (under Account & Settings).
4. Click **Invite Collaborator** in the top right.
5. Enter Developer's Email: `[Your Developer Email]`.
6. Select the appropriate role:
   - **Website Manager**: Has access to edit site, manage settings, apps, and domains (Recommended).
   - **Website Designer**: Can edit design/code but cannot manage domains or billing.
7. Click **Send Invite**.

---

### 5. Squarespace

#### How the Client Identifies It:
- Login via [Squarespace Login](https://account.squarespace.com/).
- Billing from "Squarespace".

#### What the Developer Needs:
- **Administrator** or **Website Editor** Contributor role.

#### Step-by-Step Instructions for the Client:
1. Log in to your Squarespace website.
2. From the Home Menu, click **Settings** -> **Permissions** (or **Permissions & Ownership**).
3. Click **Invite Contributor**.
4. Enter Developer's:
   - **Name**: `[Your Name]`
   - **Email**: `[Your Developer Email]`
5. Toggle the desired permissions:
   - **Administrator**: Full access to edit layout, code, injection scripts, and manage domain settings (Recommended for developers).
   - **Website Editor**: Edit pages and styles, but cannot change domain settings or code injection.
6. Click **Save** (an email invite will be dispatched).

---

### 6. WordPress.com & WP Admin

#### How the Client Identifies It:
- Client logs in via `clientwebsite.com/wp-admin` or `wordpress.com`.
- Charges from "Automattic" or "WordPress".

#### What the Developer Needs:
- **Administrator role** inside WordPress Dashboard (for theme, plugin, code, and CSS editing).
- **Hosting configuration / SFTP access** (if on WordPress.com Creator/Business plan or self-hosted).

#### Step-by-Step Instructions for the Client:
1. Log in to your website's WordPress Admin (`https://yourwebsite.com/wp-admin`).
2. In the left navigation menu, hover over **Users** and click **Add New** (or **Add User**).
3. Fill in:
   - **Username**: `[Your agency username, e.g., dev_yourname]`
   - **Email**: `[Your Developer Email]`
   - **Role**: Select **Administrator** from the dropdown (Developers require Administrator to edit themes, install plugins, and modify custom CSS/PHP).
4. Ensure **Send User Notification** is checked.
5. Click **Add New User**.

---

### 7. SiteGround

#### How the Client Identifies It:
- Login at `https://login.siteground.com/`.
- Invoices from "SiteGround Hosting".
- Nameservers: `*.siteground.biz` or `*.siteground.net`.

#### What the Developer Needs:
- **Collaborator** access to Site Tools (File Manager, FTP, MySQL, and DNS Zone Editor).

#### Step-by-Step Instructions for the Client:
1. Log in to the [SiteGround Client Area](https://login.siteground.com/).
2. Click **Websites** in the top navigation bar.
3. Next to the website you want work done on, click the **three dots (...)** or **Users**.
4. Click **Add New User**.
5. Select **Collaborator**.
6. Enter Developer's:
   - **Name**: `[Your Name]`
   - **Email**: `[Your Developer Email]`
7. If desired, check the box to allow the developer to submit support tickets on your behalf.
8. Click **Add**.

---

### 8. Bluehost (Newfold Digital)

#### How the Client Identifies It:
- Login via `https://my.bluehost.com/`.
- Billing from "Bluehost" or "Newfold Digital".

#### What the Developer Needs:
- User Access / Delegated Account management or cPanel subaccount.

#### Step-by-Step Instructions for the Client:
1. Log in to your [Bluehost Dashboard](https://my.bluehost.com/).
2. Click on the **Account Profile icon** in the top right, then click **Security** (or **User Management**).
3. Under **User Management**, click **Invite User**.
4. Enter Developer Email: `[Your Developer Email]`.
5. Assign Role: **Developer** or **Admin**.
6. Select the hosting package and domains associated with the project.
7. Click **Send Invitation**.

*(If on legacy Bluehost cPanel: Go to **Advanced** -> **FTP Accounts** or **User Manager** to create a specific developer login).*

---

### 9. WP Engine

#### How the Client Identifies It:
- Login at `https://my.wpengine.com/`.
- Premium managed WordPress invoices from "WP Engine".

#### What the Developer Needs:
- **Partial or Full Technical User** access without financial/billing privileges.

#### Step-by-Step Instructions for the Client:
1. Log in to the [WP Engine User Portal](https://my.wpengine.com/).
2. In the top navigation, click **Users** -> **Account Users**.
3. Click the purple button: **Add User**.
4. Fill in:
   - **First Name**: `[Your Name]`
   - **Last Name**: `[Your Agency]`
   - **Email**: `[Your Developer Email]`
5. In **User Roles**, choose:
   - **Full access (no billing)**: Recommended. Allows creating staging environments, Git push, SFTP, and WP Admin access.
   - Or **Partial access**: Pick only the specific Production or Staging environment.
6. Click **Invite User**.

---

### 10. Namecheap & Generic cPanel

#### How the Client Identifies It:
- Login at [Namecheap Account](https://www.namecheap.com/) or direct URL like `https://cpanel.clientwebsite.com:2083`.
- Invoices from "Namecheap" or web hosting invoices mentioning "cPanel".

#### What the Developer Needs:
- **Namecheap Profile Sharing** (for DNS & domain management) AND/OR **cPanel User / FTP Credentials**.

#### Step A: Namecheap Sharing (Domain & DNS Access):
1. Log in to Namecheap.
2. Go to **Profile** (left sidebar) -> **Sharing**.
3. Under **Managers**, click **Add Manager**.
4. Enter Developer Username/Email: `[Your Developer Name/Email]`.
5. Under Permissions, select **Domains** and **Hosting**.
6. Click **Add**.

#### Step B: Generic cPanel Access (FTP & Database):
1. Log in to cPanel.
2. Under **Files**, click **FTP Accounts**:
   - Create Username: `dev_[client]`
   - Directory: `public_html`
   - Set strong password and share via secure one-time link (e.g. Bitwarden Send).
3. Under **Preferences**, click **User Manager** to add an administrative sub-account if supported by the host.

---

## 📬 Reverse Prompt Toolkit: Copy-Paste Client Scripts

These ready-to-use email and messaging templates are tailored to communicate with non-technical clients politely and effectively.

### Template 1: The Initial Discovery Email (Send Before Kickoff)
```text
Subject: Next Steps: Website Technical Access for [Client Business Name]

Hi [Client First Name],

I am excited to start working on your new website!

To get under the hood and begin our technical evaluation, I will need access to your web hosting environment and domain settings.

Since many business owners aren't sure where these are located, here is a quick way to find them:
1. Do you know where your website is currently hosted (e.g., GoDaddy, Hostinger, Shopify, Squarespace, Wix, Bluehost)?
2. If you aren't sure, could you check your credit card or accounting records for any recurring charges under those names?

Once we know the platform, you don’t need to send me your personal password! Almost all modern hosts allow you to send me a secure "Developer Invite" using my email: [Your Developer Email].

Let me know what you find, and I will send you simple, 2-minute instructions.

Best regards,
[Your Name]
[Your Agency / Portfolio Link]
```

---

### Template 2: Delegated Access Request (Send Once Platform Is Known)
*(Example for GoDaddy; swap platform name as needed)*
```text
Subject: Quick 2-Minute Guide: Adding Me as a Delegate on GoDaddy

Hi [Client First Name],

Great news—since your domain and hosting are on GoDaddy, you can grant me developer access without sharing your personal password or credit card details!

Here are the quick steps:
1. Log into your GoDaddy account at https://account.godaddy.com/
2. Click your name in the top right corner and choose "Account Settings" -> "Delegate Access".
3. Under "People who can access my account", click "Invite to Access".
4. Enter:
   - Name: [Your Name]
   - Email: [Your Developer Email]
5. Select "Products & Domains" access level (this keeps your billing completely private).
6. Click "Invite".

Once that's done, shoot me a quick reply and I'll jump right in!

Best,
[Your Name]
```

---

### Template 3: Secure Credential Request (When Direct Login Is Unavoidable)
```text
Subject: Secure Password Handoff for [Client Website]

Hi [Client First Name],

For this specific platform, we will need direct administrator credentials to set up the developer tools.

To protect your account and ensure your passwords are never exposed over unencrypted email, please use this secure link to send your credentials:
[Insert Bitwarden Send / 1Password Share link]

Required Details:
- Login URL: (e.g., https://yourwebsite.com/wp-admin or hosting login)
- Username / Email:
- Password:

The link is encrypted and will automatically expire once viewed.

Thank you!
[Your Name]
```

---

## 🚨 Emergency Escalations & Common Roadblocks

| Symptom | Root Cause | Solution |
| :--- | :--- | :--- |
| **Client is locked out by 2-Factor Authentication (2FA)** | Previous developer set 2FA to their phone number | Have client contact hosting telephone support with proof of ownership (last 4 digits of billing card + photo ID). |
| **Domain registered in ex-agency’s account** | Vendor lock-in or misconfigured registration | Request domain transfer authorization code (EPP Code) and unlock the domain to transfer to client’s own GoDaddy/Namecheap account. |
| **DNS changes don't take effect** | High TTL (Time To Live) or Cloudflare caching | Lower TTL to 300 seconds (5 minutes) 24 hours prior to launch. Clear Cloudflare purge cache. |
| **Site crashes when updating plugins** | Incompatible PHP version or missing backups | Always generate an on-demand snapshot backup in the hosting panel (cPanel/hPanel/Site Tools) before modifying core files. |

---
*Created by Web Developer & Designer Toolkit. Powered by automated infrastructure detection.*
