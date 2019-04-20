""" Examples for exact-match faceted search """
import json
import time
import uuid

import t4
from t4.search_util import get_raw_mapping_unpacked

CONFIG_URL = 'https://quilt-t4-staging.quiltdata.com'
CONFIG_BUCKET = 's3://quilt-t4-staging'

t4.config(CONFIG_URL)
b = t4.Bucket(CONFIG_BUCKET)
b.config()

full_mapping = get_raw_mapping_unpacked(b._search_endpoint, b._region, True)

# print(json.dumps(full_mapping, indent=2))

# created by running the above code with `python test.py >> test.py`
example_mappings_object = {
  "drive": {
    "mappings": {
      "_doc": {
        "properties": {
          "comment": {
            "type": "text"
          },
          "content": {
            "type": "text"
          },
          "key": {
            "type": "keyword"
          },
          "meta": {
            "type": "object"
          },
          "meta_text": {
            "type": "text",
            "copy_to": [
              "content"
            ]
          },
          "size": {
            "type": "long",
            "copy_to": [
              "content"
            ]
          },
          "system_meta": {
            "properties": {
              "format": {
                "properties": {
                  "name": {
                    "type": "text",
                    "fields": {
                      "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                      }
                    }
                  }
                }
              }
            }
          },
          "target": {
            "type": "keyword"
          },
          "text": {
            "type": "text",
            "copy_to": [
              "content"
            ]
          },
          "type": {
            "type": "text",
            "copy_to": [
              "content"
            ]
          },
          "updated": {
            "type": "date"
          },
          "user_meta": {
            "properties": {
              "05e1b3e6-faad-4a64-b4a4-a8138129b10d": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "087f9467-2b77-46d8-bfe0-21b1a892eeab": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "1781e2d6-addb-4e39-b46d-cf5d67f048d7": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "1947a05e-9940-4ee2-b34d-53a97579bcf5": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "1b372c46-3a01-4560-87d7-a6878304efcc": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "1d58edbd-5908-4a41-81af-eb600dc2721f": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "1eb6da66-e90c-4539-a9e3-dcefebaf3684": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "2041aaf6-dee4-4b79-9d27-964b3ffb97cb": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "26998e5a-c1cd-4f9a-a7f8-4773c7b8656b": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "2f8c2384-1c2f-41f5-888f-1acffe3bce7a": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "373d48b8-24b6-4f01-8083-a21eeb1a09d2": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "39534275-f878-4134-91a5-d6e854467769": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "3cdb1426-17ec-49fc-a32c-32de15a4494d": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "4899ef0c-23db-4f99-818c-4e5fa94adef9": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "4edb1536-9acb-40e4-a51e-d6afd54d93f5": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "5862fcc1-e39c-4068-a1eb-026e3674cebd": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "5c6a4ffa-d8ea-40fa-b37d-1418af2c841b": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "60e95f94-479a-4c17-ad9b-ec8405cebd0b": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "795d96d3-3cd2-428f-8dea-e105d52b9ba2": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "8ff5681b-162b-4c66-ad46-dd04d65758a8": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "91cb50e0-d42e-4827-8fa8-335fe00a0119": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "943f0ae1-1c5e-4ca0-96e1-cfcf513c6d09": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "9483b79a-e5d6-4306-8316-e040514542e4": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "97c82ed1-d70e-4e03-9c91-8474ae472cc0": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "9add447e-25d6-4cec-9b3e-13dfee60075f": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "9ae240ed-4ac5-4de7-b30e-d2c65b8eb2df": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "a4ab1e04-ac58-4438-8b9f-7b0204d705c2": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "a94bbaa1-547a-41d1-9431-b6a1667d634f": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "b1be2cba-78a5-4a18-97b8-196bd1e3f3a0": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "bcd45147-5a8a-4a98-9751-9447edf376fe": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "c14b125b-0a75-41c4-bd07-7aeffd6108fa": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "c371c2dc-65d1-429d-8019-5a6abc639058": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "d1187da4-1383-4d35-976b-eda62d8086ac": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "d158dfb9-d9d6-4922-ac3e-51894fff0f50": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "d1fbc881-34da-4b77-a033-af6c292f0da4": {
                "type": "long"
              },
              "d5d58d4e-29ee-4efe-8dd1-54fa7ea83852": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "ebb99654-0927-40d4-a8ee-2e974d9eea3f": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "f0bd0df2-73b2-4af0-a484-6afc87ef95a6": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "f57548fe-a0c9-4c69-b52e-adecb236ac88": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              },
              "foo": {
                "type": "text",
                "fields": {
                  "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                  }
                }
              }
            }
          },
          "version_id": {
            "type": "text",
            "copy_to": [
              "content"
            ]
          }
        }
      }
    }
  }
}


# matches anything with any value for `user_meta.foo`
exists_query = {
    'query': {
        'exists': {
            'field': 'user_meta.foo'
        }
    }
}
results = b.search(exists_query)

# matches anything with a value for the field `user_meta.1781e2d6-addb-4e39-b46d-cf5d67f048d7`
nested_exists_query = {
    'query': {
        'exists': {
            'field': 'user_meta.1781e2d6-addb-4e39-b46d-cf5d67f048d7'
        }
    }
}
results = b.search(nested_exists_query)
assert results
nested_results = results

# returns everything from the last week
range_query = {
    'query': {
        'range': {
            'updated': {
                'gte': 'now-1w/d',
                'lte': 'now/d'
            }
        }
    }
}
results = b.search(range_query)

# matches anything with exactly the key 'Quilt/Package/foo.txt'
exact_match_query = {
    'query': {
        'term': {
            'key': 'Quilt/Package/foo.txt'
        }
    }
}
results = b.search(exact_match_query)

# semantically identical to previous query
single_term_query = {
    'query': {
        'bool': {
            'filter': {
                'term': {
                    'key': 'Quilt/Package/foo.txt'
                }
            }
        }
    }
}
single_term_results = b.search(single_term_query)

assert single_term_results == results

# multiple filters
multiple_term_query = {
    'query': {
        'bool': {
            'filter': [
                {
                    'term': {
                        'key': 'Quilt/Package/foo.txt'
                    }
                },
                {
                    'term': {
                        'size': 3
                    }
                }
            ]
        }
    }
}
multiple_term_results = b.search(multiple_term_query)

"""
Arrays are essentially treated as multiple indexed values for the same field,
so to search for any document that has a certain value in an array field,
you can just treat the array field as if it were a scalar field
and do an exact-match search that way.
"""
metas = []
test_key = str(uuid.uuid4())
test_meta_key = str(uuid.uuid4())
metas.append({
    test_meta_key: [1, 2, 5]
})
metas.append({
    test_meta_key: [2, 3, 5]
})
metas.append({
    test_meta_key: [3, 4, 5]
})
for meta in metas:
    b.put(test_key, '', meta=meta)

def make_number_query(number):
    return {
        'query': {
            'term': {
                'user_meta.{}'.format(test_meta_key): number
            }
        }
    }

# Give elastic time to index what we just added
time.sleep(2)

one_hits = b.search(make_number_query(1))
assert len(one_hits) == 1

two_hits = b.search(make_number_query(2))
assert len(two_hits) == 2

five_hits = b.search(make_number_query(5))
assert len(five_hits) == 3
