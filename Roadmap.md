# Roadmap

High-level overview of key features.

* [ ] Phase 1 - Jupyter Notebooks, versionsing
	* [ ] AWS SageMaker integration (abiilty to launch notebooks from T4)
	* [ ] Hosted buckets
	* [ ] T4 for AWS marketplace
	* [ ] Full version browsing + rollback support in the catalog
	* [ ] Standardize location for local/remote installs
* [ ] Phase 2 - Minio (or Ceph), everything is a bucket
	* [ ] S3-like interface for packakges, buckets, local stores
	* [ ] Examples of using packages in Spark, R, Java
	* [ ] Seamless de/serialization hooks, user-provided de/serializers
	* [ ] Improve "git for data"-layer of API
* [ ] Phase 3 - CI/CD for data science
	* [ ] Branch/merge packages
	* [ ] Git integration for CI lifecycle
	* [ ] Data unit tests
	* [ ] Declarative data profiles for unit tests
	* [ ] Data lineage visualization

* [ ] Phase 4 - Hive metastore integration
	* [ ] Discovery mechanism for hive columns/annotations (use ElasticSearch)
	* [ ] Ability to include Hive tables in packages
