# Elasticsearch API Documentation

## Description

This documentation describes the basic functionalities of the Elasticsearch API in order to create and retrieve 
documents that have been saved in the Elastic Stack. 


You can find the full documentation available on [this
page](https://elasticsearch-py.readthedocs.io/en/v8.1.1/index.html).

## Usage

### Installing

In order to use to Elasticsearch API one needs to import the python module and import the corresponding
Elasticsearch client.
```
pip3 install elasticsearch

from elasticsearch import Elasticsearch
```

### Connecting Client with Elasticsearch

Depending on the authentication method one is using there are different ways to connect to Elasticsearch.

Connection without Authentification:
```
Elastic_Client = Elasticsearch("https://localhost:9200")
```
Connection with basic Authentification:
```
Elastic_Client = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("username", "password")
)
```

Connection with API Key Authentification:
```
Elastic_Client = Elasticsearch(
    "https://localhost:9200",
    api_key=("api_key.id", "api_key.api_key")
)
```

### Indexing/Updating a document

In order to create or update a document in an index usually three parameters are needed: `index`, `id`, `document`.
If the index does not exist yet it will be created by this query.
One should check before that the document is in ECS (Elastic Common Schema) to be correctly displayed by Kibana.

You can find extended documentation on ECS available on [this
page](https://elasticsearch-py.readthedocs.io/en/v8.1.1/index.html) 
and [this page](https://www.elastic.co/guide/en/ecs/current/index.html).

```
response = Elastic_Client.index(index="test_index", id=1, document=document)
print(response)
```
One can also use the `client.create` command to create a new document in the index. It returns 409 response when 
a document with the same id already exists in the index.

```
response = Elastic_Client.create(index="test_index", id=1, document=document)
print(response)
```

Or use `client.update` to only update an existing document in a specified index:

```
response = Elastic_Client.update(index="test_index", id=1, document=document)
print(response)
```


### Getting a document

In order to get a document, you need to specify its `index` and `id`:

```
response = Elastic_Client.get(index="test_index", id=1)
print(response)
```

### Searching for a document

The `search()` method returns results that are matching a query. In the following case all documents of an specified
index are returned.

Further information about the possible parameters for the `search()` method can be found on 
[this page](https://www.elastic.co/guide/en/elasticsearch/reference/8.1/search-search.html)

```
response = Elastic_Client.search(index="test_index", query={"match_all": {}})

print("Got %d Hits:" % response['hits']['total']['value'])
for hit in response['hits']['hits']:
    print("%(@timestamp)s %(message)s" % hit["_source"])
```

The print statement above filters specified fields out of the `_source` body of each matching result.

Further example query to search for all documents in an index that match a certain `tag`:

```
response = Elastic_Client.search(index="test_index",
 query={
        "bool": {
            "must": [
                {
                    "term": {
                        "tags": {
                            "value": "train_builder_tag"
                        }
                    }
                }
            ]
        }
    })

```

The above query can be varied in order to return matches of specific fields available in the documents 
of the given index.


### Deleting a document

In order to delete a document you need to specify the `index` and `id`:

```
response = Elastic_Client.delete(index="test_index", id=1)
print(response)
```


## References
- [Python Elasticsearch Client](https://elasticsearch-py.readthedocs.io/en/v8.1.1/index.html)
