<!-- adobe · the rules that apply to every query here -->
# Always apply — adobe

Read this before writing any SQL for this product. Everything
below applies regardless of what the question asks.

### Fields containing delimited strings:

The following Adobe fields contain delimited strings:

post_event_list_by_id delimitted by ','.  See EVENT_LOOKUP to find id for specific events if the event id is not provided.
  How to search:  post_event_list_by_id like '%,event_id,%'
  Example: post_event_list_by_id like '%,176,%'

post_prop_7 Drupal Taxonomy Product ID - Product Drupal TID delimitted by ',' but value could be stand alone or prefaced with tilde i.e. 'id', 'id,', '%`~`id,' etc.  See Product Drupal TID mapping below for Drupal TID if not provided.
  How to search:  post_evar_139 ilike any ('Drupal_TID','%,Drupal_TID,%','%,Drupal_TID','%`~`Drupal_TID,%','%`~`Drupal_TIDpal_tid' )  note:"`~`" should return just the tilde
  Example: post_prop_7 ilike any ('6921','%,6921,%','%,6921','%`~`6921,%','%`~`6921')
  NOTE: use when "product taxonomy" is in user prompt.

post_prop_36 Drupal Taxonomy Topic ID - Topic Drupal TID delimitted by ',' but value could be stand alone or prefaced with tilde i.e. 'id', 'id,', '%`~`id,' etc.  See Topic Drupal TID mapping below for Drupal TID if not provided.
  How to search:  post_evar_139 ilike any ('Drupal_TID','%,Drupal_TID,%','%,Drupal_TID','%`~`Drupal_TID,%','%`~`Drupal_TID' )  note:"`~`" should return just the tilde
  example: post_prop_36 ilike any ('4491','%,4491,%','%,4491','%`~`4491,%','%`~`4491')
  NOTE: use when "topic taxonomy" is in user prompt.

post_evar_139 - Target Topic Affinity - Topic Drupal TID delimitted by '|'.  See Topic Drupal TID mapping below for Drupal TID if not provided.
  How to search:  post_evar_139 ilike ('Drupal_TID','%|Drupal_TID|%','%|Drupal_TID' )
  Example: post_evar_139 ilike ('9011','%|9011|%','%|9011' )
  note: DO NOT USE post_evar_139 unless "Topic Affinity" is in user prompt.

post_evar_140 - Target Product Affinity - Product Drupal TID delimitted by '|'  See Product Drupal TID mapping below for Drupal TID if not provided.
  How to search:  post_evar_139 ilike ('Drupal_TID','%|Drupal_TID|%','%|Drupal_TID' )
  Example: post_evar_139 ilike ('6921','%|6921|%','%|6921' )
  note: DO NOT USE  post_evar_140 unless "product affinity" is in user prompt.

Product Drupal TID mapping (used by post_prop_7, post_evar_140):
  Product	Product line mapping	Drupal_TID
  Microsoft Azure Red Hat OpenShift	Cloud computing	80291
  Red Hat 3scale API Management	Application services	22571
  Red Hat Advanced Cluster Management for Kubernetes	Management	65761
  Red Hat Advanced Cluster Security for Kubernetes	Management	78331
  Red Hat Advanced Developer Suite	Cloud computing	109391
  Red Hat AI	AI	108951
  Red Hat AI Enterprise	AI	114131
  Red Hat AI Factory with NVIDIA	AI	114141
  Red Hat AI Inference	AI	109181
  Red Hat AMQ	Application services	4561
  Red Hat Ansible Automation Platform	Management	25911
  Red Hat Ansible Automation Platform on Microsoft Azure	Management	82831
  Red Hat Ansible Automation Platform via AWS	Management	107131
  Red Hat Ansible Automation Platform via Google Cloud	Management	107121
  Red Hat Application Foundations	Application services	82031
  Red Hat Certificate System	Cloud computing	1921
  Red Hat Connectivity Link	Application services	108221
  Red Hat Data Grid	Application services	1961
  Red Hat Desktop	Cloud computing	114441
  Red Hat Developer Hub	Cloud computing	107381
  Red Hat Device Edge	Cloud computing	107021
  Red Hat Directory Server	Cloud computing	1941
  Red Hat Enterprise Linux	Linux platforms	781
  Red Hat Enterprise Linux AI	AI	107881
  Red Hat Enterprise Linux for SAP Solutions	Linux platforms	82841
  Red Hat Enterprise Linux for Workstations	Linux platforms	107091
  Red Hat Enterprise Linux Server	Linux platforms	107101
  Red Hat JBoss Enterprise Application Platform	Application services	1931
  Red Hat JBoss Web Server	Application services	4911
  Red Hat Lightspeed	Management	18951
  Red Hat OpenShift	Cloud computing	6921
  Red Hat OpenShift AI	AI	80251
  Red Hat OpenShift Container Platform	Cloud computing	82861
  Red Hat OpenShift Dedicated	Cloud computing	80261
  Red Hat OpenShift Kubernetes Engine	Cloud computing	82881
  Red Hat OpenShift on IBM Cloud	Cloud computing	80331
  Red Hat OpenShift Platform Plus	Cloud computing	82891
  Red Hat OpenShift Service on AWS	Cloud computing	80281
  Red Hat OpenShift Virtualization	Cloud computing	107391
  Red Hat OpenShift Virtualization Engine	Cloud computing	108761
  Red Hat OpenStack Services on OpenShift	Cloud computing	6941
  Red Hat Quay	Cloud computing	27421
  Red Hat Runtimes	Application services	46091
  Red Hat Satellite	Management	801
  Red Hat Service Interconnect	Cloud computing	107041
  Red Hat Trusted Software Supply Chain	Cloud computing	107031Product	Product line mapping	Drupal TID
  Microsoft Azure Red Hat OpenShift	Cloud computing	80291
  Red Hat 3scale API Management	Application services	22571
  Red Hat Advanced Cluster Management for Kubernetes	Management	65761
  Red Hat Advanced Cluster Security for Kubernetes	Management	78331
  Red Hat Advanced Developer Suite	Cloud computing	109391
  Red Hat AI	AI	108951
  Red Hat AI Enterprise	AI	114131
  Red Hat AI Factory with NVIDIA	AI	114141
  Red Hat AI Inference	AI	109181
  Red Hat AMQ	Application services	4561
  Red Hat Ansible Automation Platform	Management	25911
  Red Hat Ansible Automation Platform on Microsoft Azure	Management	82831
  Red Hat Ansible Automation Platform via AWS	Management	107131
  Red Hat Ansible Automation Platform via Google Cloud	Management	107121
  Red Hat Application Foundations	Application services	82031
  Red Hat Certificate System	Cloud computing	1921
  Red Hat Connectivity Link	Application services	108221
  Red Hat Data Grid	Application services	1961
  Red Hat Desktop	Cloud computing	114441
  Red Hat Developer Hub	Cloud computing	107381
  Red Hat Device Edge	Cloud computing	107021
  Red Hat Directory Server	Cloud computing	1941
  Red Hat Enterprise Linux	Linux platforms	781
  Red Hat Enterprise Linux AI	AI	107881
  Red Hat Enterprise Linux for SAP Solutions	Linux platforms	82841
  Red Hat Enterprise Linux for Workstations	Linux platforms	107091
  Red Hat Enterprise Linux Server	Linux platforms	107101
  Red Hat JBoss Enterprise Application Platform	Application services	1931
  Red Hat JBoss Web Server	Application services	4911
  Red Hat Lightspeed	Management	18951
  Red Hat OpenShift	Cloud computing	6921
  Red Hat OpenShift AI	AI	80251
  Red Hat OpenShift Container Platform	Cloud computing	82861
  Red Hat OpenShift Dedicated	Cloud computing	80261
  Red Hat OpenShift Kubernetes Engine	Cloud computing	82881
  Red Hat OpenShift on IBM Cloud	Cloud computing	80331
  Red Hat OpenShift Platform Plus	Cloud computing	82891
  Red Hat OpenShift Service on AWS	Cloud computing	80281
  Red Hat OpenShift Virtualization	Cloud computing	107391
  Red Hat OpenShift Virtualization Engine	Cloud computing	108761
  Red Hat OpenStack Services on OpenShift	Cloud computing	6941
  Red Hat Quay	Cloud computing	27421
  Red Hat Runtimes	Application services	46091
  Red Hat Satellite	Management	801
  Red Hat Service Interconnect	Cloud computing	107041
  Red Hat Trusted Software Supply Chain	Cloud computing	107031

Topic Drupal TID mapping (used by post_prop_36 and post_evar_139):
  Topic	Drupal_TID
  AI inference	109861
  APIs	27001
  Application development and delivery	27031
  Application modernization	82041
  Artificial intelligence	75501
  Automation and management	27011
  Cloud automation	107311
  Cloud services	75491
  Containers	9001
  Culture and process	27021
  Customer success	4471
  Data science	8401
  DevOps	8391
  Digital sovereignty	114041
  Edge computing	75331
  Events	1341
  Hardened images	114431
  Hybrid cloud	9011
  Integration	27051
  Linux	27061
  Managed cloud	107261
  Network automation	107301
  Observability	107901
  Open source	17391
  Partners	4481
  Platform engineering	108861
  Professional development	107491
  Security	4491
  Tech history	107481
  Virtualization	27111
  Zero trust	114051

## Handling of Salesforce account_id
Rule:  when prompted to retrieve adobe data based on Salesforce account id's join POST_EVAR_63 against the EBS_ACCOUNT_NUMBER using the ebs_bridge logic
- **ebs_bridge sql**:  WITH ebs_bridge AS ( SELECT DISTINCT r.EBS_ACCOUNT_NUMBER FROM ROSETTASTONE_DB.MARTS.MDM_RHSC_EBS_ENHANCED_MAPPING r JOIN SFSALES_DB.MARTS.ACCOUNT_MDM_PARTY amp ON r.MDM_PARTY_ID = amp.MDM_PARTY_ID WHERE amp.SFL_ACCOUNT_ID = '<Salesforce account id>' )

## Query Performance Notes

1. **Date Filtering**: ALWAYS filter on `date_time` or `hit_time_gmt` to limit scan size
2. **Avoid Unbounded Scans**: ALWAYS Use `LIMIT` or aggregation when exploring; table can be large.  Limit all queries to a max of 100 rows.
3. **post_evar Columns**: Many `post_evar_`* columns exist; use only those needed (e.g., `post_evar_1` for page name)
4. **Incremental Model**: Table is incremental on `_fivetran_synced`; historical data is retained

---

## Routing

**When to route here:**

- Adobe Analytics hit-level data
- Web analytics, page views, sessions
- Marketing touchpoints, campaign attribution
- Visitor/geo/device analytics from Adobe

**When NOT to route here:**

- Email campaign data (Marketo) → Use **Marketo**
- CRM/lead data → Use **Marketo** or **Salesforce**
