---
name: tfs-rest-api
description: Query and manage TFS (Azure DevOps Server) work items via REST API — WIQL queries, CRUD, linking, state transitions.
tags: [tfs, azure-devops, rest-api, work-items, wiql]
---

# TFS (Azure DevOps Server) REST API

Manage work items on on-premise Azure DevOps Server (TFS) via REST API using PAT authentication.

## Authentication

Use Personal Access Token (PAT) with HTTP Basic auth:
```bash
curl -u ":<PAT>" "http://<tfs-host>/DefaultCollection/_apis/..."
```

Or in Python:
```python
import base64
credentials = base64.b64encode((':' + pat).encode()).decode()
headers = {'Authorization': 'Basic ' + credentials}
```

## Key API Endpoints

| Action | Method | URL |
|--------|--------|-----|
| List projects | GET | `/_apis/projects?api-version=2.0` |
| WIQL query | POST | `/{project}/_apis/wit/wiql?api-version=2.0` |
| Get work item | GET | `/_apis/wit/workitems/{id}?api-version=2.0` |
| Get multiple | GET | `/_apis/wit/workitems?ids=1,2,3&fields=...&api-version=2.0` |
| Create work item | POST | `/{project}/_apis/wit/workitems/${type}?api-version=2.0` |
| Update work item | PATCH | `/_apis/wit/workitems/{id}?api-version=2.0` |
| List iterations | GET | `/{project}/_apis/wit/classificationnodes/iterations?$depth=3&api-version=2.0` |
| List fields | GET | `/{project}/_apis/wit/fields?api-version=2.0` |
| Work item types | GET | `/{project}/_apis/wit/workitemtypes?api-version=2.0` |

## WIQL Queries

POST JSON body with `query` field to the WIQL endpoint. Use Unicode escapes for Chinese characters:

```json
{
  "query": "SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE [System.TeamProject] = @Project AND [System.AssignedTo] = @Me AND [System.WorkItemType] = '用户情景' ORDER BY [System.Id] DESC"
}
```

**Important**: Response only returns work item IDs and URLs. Must make a second call to get field details.

## Steps: Create Child Task Under User Story

1. Write JSON patch body to a file (avoids shell escaping issues)
2. Use `curl -d @file.json` to POST
3. Must include all required fields or creation fails

## Critical Pitfalls

### 1. Content-Type for Create/Update
```
Content-Type: application/json-patch+json
```
NOT `application/json`. The create/update endpoints use JSON Patch format (array of ops).

### 2. Create URL Must Include Project
```
/{project}/_apis/wit/workitems/${url_encoded_type}?api-version=2.0
```
NOT `/_apis/wit/workitems/...`. The project name MUST be in the URL path.

### 3. Required Fields for Task Creation
Tasks require these fields at minimum:
- `System.Title`
- `Microsoft.VSTS.Scheduling.RemainingWork` (number, e.g. 8)
- `Microsoft.VSTS.Scheduling.OriginalEstimate` (number, e.g. 8)
- `Microsoft.VSTS.Common.Activity` (e.g. "开发")
- `System.IterationPath`

### 4. Closing a Task — RemainingWork Must Be EMPTY
When setting state to "已关闭", `RemainingWork` must be removed/empty, NOT set to 0.
Setting it to 0 causes: `TF401320: 字段 剩余工作 发生规则错误。错误代码: InvalidNotEmpty。`

Solution: Don't include RemainingWork in the close operation. Just set state + CompletedWork.

### 5. AreaPath/IterationPath Backslash Escaping
When writing JSON via Python string literals, backslashes get eaten. 
**Solution**: Write JSON to a file first, then use `curl -d @file.json`:

```python
with open('tfs_update.json', 'w', encoding='utf-8') as f:
    f.write('[{"op": "replace", "path": "/fields/System.AreaPath", "value": "XiNanArea-New\\\\四川省区团队"}]')
```

Or use `write_file` tool to write literal JSON, then curl it.

### 6. Finding Correct Iteration Names
Iteration names may have inconsistent spacing (e.g., "迭代 2026-4-4" vs "迭代2026-5-1").
Always query classification nodes to get exact names:
```
GET /{project}/_apis/wit/classificationnodes/iterations?$depth=3&api-version=2.0
```

### 7. Linking as Child (Parent-Child Relation)
Use `System.LinkTypes.Hierarchy-Reverse` relation to create a child:
```json
{
  "op": "add",
  "path": "/relations/-",
  "value": {
    "rel": "System.LinkTypes.Hierarchy-Reverse",
    "url": "http://<tfs>/DefaultCollection/_apis/wit/workItems/<parent_id>"
  }
}
```

### 8. Custom Fields
Custom fields use GUID reference names. Find them via:
```
GET /{project}/_apis/wit/fields?api-version=2.0
```
Then filter by name. Example: "需求交付负责人" = `Custom.3d3cdcf5-de35-4448-afbb-bdfd963d2564`

### 9. WIQL with Custom Fields
Custom fields can be used in WIQL queries by their reference name:
```
WHERE [Custom.3d3cdcf5-de35-4448-afbb-bdfd963d2564] = @Me
```

### 10. Batch Fetching Work Item Details
WIQL returns IDs only. Fetch details in batches of 200:
```
GET /_apis/wit/workitems?ids=1,2,...,200&fields=System.Id,System.Title,System.State&api-version=2.0
```

### 11. Creating Work Items with Chinese Type Names
The URL path for creating work items with Chinese type names (e.g. `任务`) MUST use URL encoding:
```
POST /{project}/_apis/wit/workitems/$%E4%BB%BB%E5%8A%A1?api-version=2.0
```
Python `urllib.parse.quote('任务')` produces `%E4%BB%BB%E5%8A%A1`.
**Do NOT** pass the raw Chinese characters in the URL — Python's `http.client` will fail with `UnicodeEncodeError: 'ascii' codec can't encode`.
**Always use `curl -d @file.json`** for requests involving Chinese in the URL path.

### 12. Closing a 用户情景 Requires 3 Mandatory Evaluation Fields
When transitioning a 用户情景 to 已关闭, TFS requires three picklist fields:
- **质量评价** (`Custom.a6fb40d4-5f26-4167-b47c-b056ab423f49`)
- **服务态度** (`Custom.2286db83-008a-4bbc-bdd2-98a779a142d6`)
- **用户体验** (`Custom.b7a089cf-99c0-4d5c-ab03-8bd3f068194f`)

If missing, returns: `TF401320: 字段 质量评价 发生规则错误。错误代码: Required, HasValues, LimitedToValues, AllowsOldValue, InvalidEmpty。`

Valid values (all 5-score):
```
质量评价: 5-功能完备可正常运行，满足使用
服务态度: 5-服务亲切热情且耐心好
用户体验: 5-界面美观、布局合理、呈现清晰、操作极简
```

To discover valid values for any picklist field, find an existing closed item with values populated:
```
WIQL: SELECT [System.Id] FROM WorkItems WHERE [Custom.a6fb40d4-...] <> '' AND [System.State] = '已关闭'
```

## Quick Reference: Common Operations

See `references/api-examples.md` for ready-to-use curl/Python snippets for common tasks.
