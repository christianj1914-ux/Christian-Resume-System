# Practical Skills Reference
### SQL, Excel, Power BI, Azure, AWS, and binary. Hands-on, for the roles you are actually applying to.

**Bottom line up front:** these are the doing skills that show up across your implementation, technical-consultant, ERP, and analytics applications. **SQL is the single highest-leverage one**, because every one of those roles queries or moves data. Learn by doing: run a query, build a pivot, make a chart. Reading is not enough here.

---

## 1. SQL (learn this first)

**Why it matters for you:** technical consultants, ERP admins, and every BI or data-analyst role query data. You already did ETL and data migration at East West, so this is formalizing a strength.

**Practice environment (no install):** sqliteonline.com or DB Fiddle. Load a sample table and run everything below.

**Clause order (always this order):** `SELECT ... FROM ... WHERE ... GROUP BY ... HAVING ... ORDER BY ... LIMIT`

**Core queries:**
```
SELECT name, email FROM customers;
SELECT * FROM orders WHERE status = 'open' AND total > 100;
SELECT * FROM orders ORDER BY total DESC LIMIT 10;
SELECT status, COUNT(*), SUM(total) FROM orders GROUP BY status;
SELECT customer_id FROM orders GROUP BY customer_id HAVING SUM(total) > 1000;
```
- **WHERE vs HAVING:** WHERE filters rows before grouping; HAVING filters groups after.

**Joins (the skill that separates beginners from real users):**
```
SELECT c.name, o.total
FROM customers c
JOIN orders o ON o.customer_id = c.id;          -- INNER JOIN: matches in both

SELECT c.name
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.id IS NULL;                             -- customers with no orders
```

**The rest you will use constantly:** `DISTINCT`, aliases (`AS`), `COUNT/SUM/AVG/MIN/MAX`, `LIKE '%text%'`, `IN (...)`, `BETWEEN a AND b`, `IS NULL`, `CASE WHEN ... THEN ... ELSE ... END`, subqueries, and CTEs (`WITH t AS (...) SELECT ...`).

**Changing data (always include WHERE):**
```
INSERT INTO customers (name) VALUES ('Acme');
UPDATE orders SET status = 'closed' WHERE id = 5;
DELETE FROM orders WHERE id = 5;
```
Forget the WHERE and you change or delete every row. This is the classic career-defining mistake; do not make it.

**One-week practical path:** Day 1 SELECT/WHERE/ORDER; Day 2 GROUP BY/HAVING and aggregates; Day 3 JOINs; Day 4 subqueries and CTEs; Day 5 CASE, dates, strings; Day 6 INSERT/UPDATE/DELETE; Day 7 answer five business questions against a sample database.

**Free resources:** SQLBolt (interactive), Mode SQL Tutorial, W3Schools SQL, and the book "SQL for Data Analysis" (Cathy Tanimura).

**Interview line:** "I use SQL to pull and validate data, join across tables, and aggregate for reporting. I did the ETL and data migration at East West, so I am comfortable in a database, not just a spreadsheet."

---

## 2. Excel (shortcuts and general tips)

**Shortcuts that save real time (Windows):**

| Shortcut | Does |
|---|---|
| Ctrl + Arrow | Jump to the edge of the data |
| Ctrl + Shift + Arrow | Select to the edge of the data |
| Ctrl + Home / End | Go to A1 / the last used cell |
| Alt + = | AutoSum |
| F4 | Toggle absolute reference ($), or repeat last action |
| Ctrl + T | Make a Table |
| Ctrl + Shift + L | Toggle filters |
| Ctrl + 1 | Format Cells dialog |
| Ctrl + ; | Insert today's date |
| F2 | Edit the active cell |
| Ctrl + Enter | Fill the whole selection with your entry |
| Ctrl + Space / Shift + Space | Select column / row |
| Ctrl + PgUp / PgDn | Switch worksheets |

**Functions to know cold:** `SUM, AVERAGE, COUNT, COUNTA`; `SUMIF(S), COUNTIF(S), AVERAGEIF(S)`; `IF, IFS, AND, OR, IFERROR`; `XLOOKUP` (prefer it over VLOOKUP) and `INDEX + MATCH`; `TRIM, LEFT/RIGHT/MID, LEN, CONCAT or &`; `TODAY, EOMONTH, DATEDIF`; dynamic arrays `UNIQUE, FILTER, SORT`.

**General tips:** use Tables (Ctrl + T) so formulas reference named columns; keep raw data on its own sheet, separate from analysis; PivotTables are the analyst's power tool (drag fields to summarize); Power Query (Get and Transform) cleans and reshapes messy data repeatably; XLOOKUP beats VLOOKUP (no column-counting, looks left, cleaner).

---

## 3. Power BI

**The flow:** Get data (Power Query) -> model the data (relationships) -> write DAX measures -> build visuals -> publish.

- **Power Query:** clean and shape before you model (remove columns, unpivot, merge, append).
- **Data model:** build a star schema, one fact table (events, like Sales) linked to dimension tables (Date, Product, Customer). Relationships are one-to-many. Mark your Date table.
- **DAX:** measures (calculated on the fly) beat calculated columns (stored per row). Key functions: `SUM`, `CALCULATE` (the most important, it changes filter context), `FILTER`, `SUMX`, `DIVIDE` (use instead of `/`), `RELATED`, `ALL`, `DISTINCTCOUNT`, and time intelligence like `TOTALYTD` and `SAMEPERIODLASTYEAR`.
```
Total Sales = SUM(Sales[Amount])
Sales YTD  = TOTALYTD([Total Sales], 'Date'[Date])
Margin %   = DIVIDE([Profit], [Total Sales])
```
- **Visuals:** line for trends, bar for comparisons, cards for KPIs, slicers to filter, matrix for tables; add drill-through and bookmarks for interactivity.
- **Cert:** PL-300.

---

## 4. Azure (AZ-900 fundamentals)

- **Compute:** Virtual Machines (IaaS), App Service (PaaS web apps), Azure Functions (serverless), AKS (Kubernetes).
- **Storage:** Blob Storage (objects), Azure Files, Managed Disks.
- **Databases:** Azure SQL Database (relational), Cosmos DB (NoSQL), Synapse (analytics/warehouse).
- **Networking:** Virtual Network (VNet), Load Balancer, VPN Gateway, Azure DNS.
- **Identity:** Microsoft Entra ID (formerly Azure AD) with RBAC (role-based access control).
- **Management and governance:** Resource Groups, Azure Resource Manager (ARM), Azure Monitor, Cost Management, Azure Policy, Management Groups.
- **AI:** Azure AI services, Azure OpenAI, Azure Machine Learning.
- **Concepts:** hierarchy is Management Group > Subscription > Resource Group > Resource; regions and availability zones; shared responsibility; pay-as-you-go.
- **Cert path:** AZ-900 (fundamentals), then AZ-104 (admin); AI-900 and PL-300 pair well.

---

## 5. AWS (fundamentals, quick recall) and the Azure map

- **Compute:** EC2, Lambda, ECS/EKS, Fargate. **Storage:** S3, EBS, EFS, Glacier. **Databases:** RDS, Aurora, DynamoDB, ElastiCache, Redshift. **Networking:** VPC, Route 53, CloudFront, ELB. **Identity/security:** IAM, KMS, Security Groups (stateful) vs NACLs (stateless). **Management:** CloudWatch, CloudTrail, CloudFormation, Cost Explorer.

**Azure-to-AWS quick map (useful in interviews):**

| Need | Azure | AWS |
|---|---|---|
| Virtual machines | Virtual Machines | EC2 |
| Object storage | Blob Storage | S3 |
| Serverless functions | Azure Functions | Lambda |
| Managed SQL | Azure SQL Database | RDS |
| NoSQL | Cosmos DB | DynamoDB |
| Network | VNet | VPC |
| Identity | Entra ID + RBAC | IAM |
| Monitoring | Azure Monitor | CloudWatch |

- **Cert path:** Cloud Practitioner (CLF-C02), then Solutions Architect Associate (SAA-C03). Full depth is in your AWS track.

---

## 6. Binary counting for networking (the deep version)

### Counting in binary
Binary uses only 0 and 1. Each position, right to left, is worth double the last: 1, 2, 4, 8, 16, 32, 64, 128.

Counting 0 to 15 in four bits shows the pattern (the rightmost bit flips every count, the next every two, the next every four):
```
0000=0  0001=1  0010=2  0011=3
0100=4  0101=5  0110=6  0111=7
1000=8  1001=9  1010=10 1011=11
1100=12 1101=13 1110=14 1111=15
```

### Powers of 2 (memorize)
2^0..2^10 = 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024. In one octet the bit values are **128 64 32 16 8 4 2 1**.

### Convert both directions
- **Decimal to binary:** subtract the largest bit value that fits, repeat. 200 = 128 + 64 + 8 -> `11001000`. 37 = 32 + 4 + 1 -> `00100101`.
- **Binary to decimal:** add the values where the bit is 1. `10101100` = 128 + 32 + 8 + 4 = 172.

### Hexadecimal (base 16)
Digits 0-9 then A-F (10 to 15). One hex digit equals four bits (a nibble), so two hex digits equal one byte. `FF` = `1111 1111` = 255. IPv6 and MAC addresses use hex.

### Subnetting, deep
- A subnet mask is network bits (1s) then host bits (0s). `/24` = `255.255.255.0`.
- Interesting-octet mask values: **/25=128, /26=192, /27=224, /28=240, /29=248, /30=252.**
- **Usable hosts = 2^(host bits) - 2.** **Block size = 256 - mask value** in the interesting octet.
- **Fast method:** find the interesting octet, get the block size, list its multiples (0, block, 2xblock ...), round the address down to the nearest multiple for the network, and the broadcast is the next network minus one.
- **Worked (192.168.1.0/26):** block size 64 -> subnets .0, .64, .128, .192; each has 62 usable; the .0 subnet is network .0, broadcast .63, hosts .1 to .62.
- **VLSM:** when carving one network into different sizes, allocate the largest subnet first.
- **Wildcard mask (used in ACLs):** the inverse of the subnet mask. `/24` -> `0.0.0.255`.

### Drills (answers below)
1. Write 0 to 8 in binary.
2. Convert to binary: 88, 172, 255.
3. Convert to decimal: `01011010`, `11110000`.
4. `/27`: how many usable hosts?
5. Which `/26` subnet contains 192.168.1.100?
6. Subnet mask for `/28` in dotted decimal?

**Answers:** 1. 0,1,10,11,100,101,110,111,1000. 2. 88=`1011000`, 172=`10101100`, 255=`11111111`. 3. `01011010`=90, `11110000`=240. 4. 30. 5. the .64 subnet (.64 to .127). 6. 255.255.255.240.

---
*Companion to your learning guide, cheat sheets, and flashcards. SQL, Excel, and Azure now have their own flashcard decks; binary and Power BI were deepened in Foundations and Data & BI.*
