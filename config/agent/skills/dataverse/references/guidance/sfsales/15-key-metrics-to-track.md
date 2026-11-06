<!-- sfsales · from 02-advanced-analysis-patterns.md -->
### Key Metrics to Track
1. **Pipeline Health**: Pipeline velocity, stage conversion rates, and forecast accuracy
2. **Sales Performance**: Rep productivity, quota attainment, and win rates
3. **Customer Analytics**: Account penetration, customer lifetime value, and retention
4. **Product Performance**: Product attach rates, pricing realization, and bundle effectiveness
5. **Market Intelligence**: Competitive win/loss rates, market share trends, and pricing pressure

### Executive Reporting Patterns
- **Weekly Pipeline Reviews**: Stage progression, deal risk assessment, forecast accuracy
- **Monthly Performance Reports**: Rep performance, territory coverage, quota tracking
- **Quarterly Business Reviews**: Revenue recognition, market analysis, competitive positioning
- **Annual Planning**: Territory realignment, quota setting, market expansion strategy

## 🔒 Data Governance & Security

### Access Controls
- **Territory-Based Access**: Users typically see only their assigned territories and accounts
- **Role-Based Permissions**: Different access levels based on sales roles and responsibilities
- **Record Sharing**: Complex sharing rules for account teams and opportunity access
- **Historical Data**: Maintain audit trails for all opportunity and account changes

### Data Quality Standards
- **Required Fields**: Enforce completion of critical opportunity and account fields
- **Validation Rules**: Business rules for stage progression and data consistency
- **Duplicate Management**: Account and contact deduplication processes
- **Currency Management**: Proper handling of multi-currency transactions and conversions

---

## 📚 Table Reference Quick Guide

### Core Sales Tables
- **`opportunity`**: Primary sales opportunity tracking with complete deal lifecycle
- **`account`**: Customer and prospect account information with hierarchy relationships
- **`contact`**: Individual contact details within customer organizations
- **`user`**: Sales team member profiles and territory assignments

### Revenue & Product Tables
- **`opportunity_product`**: Line-item details for multi-product opportunities
- **`product`**: Master product catalog with hierarchy and pricing information
- **`orders`**: Closed-won order details and fulfillment information
- **`quote`**: Quote and proposal information for opportunities

### Relationship & Structure Tables
- **`opportunity_partner`**: Channel partner associations and deal registration
- **`account_team_member`**: Account coverage and team assignments
- **`territory`**: Territory definitions and coverage models
- **`campaign`**: Marketing campaign tracking and attribution
