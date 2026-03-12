import sys
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext


def get_optional_arg(args, key, default=None):
    flag = f"--{key}"
    if flag in sys.argv:
        return getResolvedOptions(sys.argv, [key]).get(key, default)
    return default


def main():
    required = ["JOB_NAME"]
    resolved = getResolvedOptions(sys.argv, required)

    sc = SparkContext()
    glue_context = GlueContext(sc)
    spark = glue_context.spark_session
    job = Job(glue_context)
    job.init(resolved["JOB_NAME"], resolved)

    source_path = get_optional_arg(sys.argv, "source_path")
    target_path = get_optional_arg(sys.argv, "target_path")

    print(f"Starting Glue job: {resolved['JOB_NAME']}")
    print(f"source_path={source_path}")
    print(f"target_path={target_path}")

    if source_path and target_path:
        df = spark.read.format("parquet").load(source_path)
        df.write.mode("overwrite").format("parquet").save(target_path)
        print("Data copy completed successfully")
    else:
        print("No source_path/target_path provided; scaffold job completed without data movement")

    job.commit()


if __name__ == "__main__":
    main()
