# CMS API mocks (WordPress, Webflow, Contentful)

Three CMS integrations supply **content inventory** that complements GSC/GA4 landing-page performance data. Report generation remains GSC-only; CMS data appears in Step 2 extract.

## Fixture layout

```
data/mock_inputs/cms/
  customers.json          # per-customer siteUrl, collectionId, space, environment
  wordpress/{customer}.json
  webflow/{customer}.json
  contentful/{customer}.json
```

Content paths align with GSC `topPages` (e.g. `/blog/protein-guide`).

## Endpoints mocked

| Source | API | Mock method |
|--------|-----|-------------|
| WordPress | `GET /wp-json/wp/v2/posts` | `list_posts` |
| Webflow | `GET /v2/collections/{collection_id}/items/live` | `list_live_items` |
| Contentful | `GET /spaces/{space}/environments/{env}/entries` (CDA) | `list_entries` |

## Python modules

| Module | Role |
|--------|------|
| [`engine/cms/wordpress.py`](../engine/cms/wordpress.py) | `MockWordPressClient` |
| [`engine/cms/webflow.py`](../engine/cms/webflow.py) | `MockWebflowClient` |
| [`engine/cms/contentful.py`](../engine/cms/contentful.py) | `MockContentfulClient` |
| [`engine/cms/adapters.py`](../engine/cms/adapters.py) | Normalize API bodies for extract |
| [`engine/cms/service.py`](../engine/cms/service.py) | `CmsMockService` |
| [`engine/sources.py`](../engine/sources.py) | `WordPressSource`, `WebflowSource`, `ContentfulSource` |

## Extract item IDs

**WordPress:** `wordpress.kpi.published-posts`, `wordpress.post.<slug>`

**Webflow:** `webflow.kpi.live-items`, `webflow.item.<slug>`

**Contentful:** `contentful.kpi.entries`, `contentful.entry.<slug>`

## HTTP debug routes

```bash
curl "http://127.0.0.1:8000/api/wordpress/posts?customerId=acme-health"
curl "http://127.0.0.1:8000/api/webflow/items?customerId=acme-health"
curl "http://127.0.0.1:8000/api/contentful/entries?customerId=acme-health"
```

## Official references

- [WordPress REST API – Posts](https://developer.wordpress.org/rest-api/reference/posts/)
- [Webflow CMS API – List Live Items](https://developers.webflow.com/data/reference/cms/collection-items/live-items/list-items-live)
- [Contentful Content Delivery API – Entries](https://www.contentful.com/developers/docs/references/content-delivery-api/)
