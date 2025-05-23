# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import time
import datetime
import argparse
import asyncio
import os
import logging
from collections import defaultdict
from functools import partial
from dotenv import load_dotenv

from azure.identity.aio import ClientSecretCredential, DefaultAzureCredential
from azure.eventhub.aio import EventHubConsumerClient
from azure.eventhub import EventHubSharedKeyCredential
from azure.eventhub.extensions.checkpointstoreblobaio import BlobCheckpointStore
from azure.eventhub import TransportType

from logger import get_logger
from process_monitor import ProcessMonitor
from app_insights_metric import AzureMonitorMetric

ENV_FILE = os.environ.get("ENV_FILE")
load_dotenv(dotenv_path=ENV_FILE, override=True)


def parse_starting_position(args):
    starting_position = None
    if args.starting_offset:
        starting_position = str(args.starting_offset)
    if args.starting_sequence_number:
        starting_position = int(args.starting_sequence_number)
    if args.starting_datetime:
        starting_position = datetime.datetime.strptime(str(args.starting_datetime), "%Y-%m-%d %H:%M:%S")

    if not starting_position:
        starting_position = "-1"

    return starting_position


parser = argparse.ArgumentParser()
parser.add_argument("--link_credit", default=int(os.environ.get("LINK_CREDIT", 3000)), type=int)
parser.add_argument("--output_interval", type=float, default=int(os.environ.get("OUTPUT_INTERVAL", 5000)))
parser.add_argument(
    "--duration", help="Duration in seconds of the test", type=int, default=int(os.environ.get("DURATION", 999999999))
)
parser.add_argument(
    "--consumer_group", help="Consumer group name", default=os.environ.get("CONSUMER_GROUP", "$default")
)
parser.add_argument("--auth_timeout", help="Authorization Timeout", type=float, default=60)
parser.add_argument(
    "--starting_offset", help="Starting offset", type=str, default=os.environ.get("STARTING_OFFSET", "-1")
)
parser.add_argument("--starting_sequence_number", help="Starting sequence number", type=int)
parser.add_argument("--starting_datetime", help="Starting datetime string, should be format of YYYY-mm-dd HH:mm:ss")
parser.add_argument(
    "--partitions", help="Number of partitions. 0 means to get partitions from eventhubs", type=int, default=0
)
parser.add_argument("--owner_level", help="The owner level, or epoch, of the consumer", type=int, default=None)
parser.add_argument("--recv_partition_id", help="Receive from a specific partition if this is set", type=int)
parser.add_argument(
    "--max_batch_size",
    type=int,
    default=int(os.environ.get("MAX_BATCH_SIZE", 0)),
    help="Call EventHubConsumerClient.receive_batch() if not 0, otherwise call receive()",
)
parser.add_argument(
    "--max_wait_time",
    type=float,
    default=0,
    help="max_wait_time of EventHubConsumerClient.receive_batch() or EventHubConsumerClient.receive()",
)

parser.add_argument("--track_last_enqueued_event_properties", action="store_true")
parser.add_argument(
    "--load_balancing_interval", help="time duration in seconds between two load balance", type=float, default=10
)
parser.add_argument("--conn_str", help="EventHub connection string", default=os.environ.get("EVENT_HUB_CONN_STR"))
parser.add_argument("--azure_identity", help="Use identity", type=bool, default=False)
parser.add_argument(
    "--hostname",
    help="The fully qualified host name for the Event Hubs namespace.",
    default=os.environ.get("EVENT_HUB_HOSTNAME"),
)
parser.add_argument("--eventhub", help="Name of EventHub", default=os.environ.get("EVENT_HUB_NAME"))
parser.add_argument("--address", help="Address URI to the EventHub entity")
parser.add_argument("--sas_policy", help="Name of the shared access policy to authenticate with")
parser.add_argument("--sas_key", help="Shared access key")
parser.add_argument(
    "--transport_type", help="Transport type, 0 means AMQP, 1 means AMQP over WebSocket", type=int, default=0
)
parser.add_argument(
    "--parallel_recv_cnt", help="Number of receive clients doing parallel receiving", type=int, default=1
)
parser.add_argument("--proxy_hostname", type=str)
parser.add_argument("--proxy_port", type=str)
parser.add_argument("--proxy_username", type=str)
parser.add_argument("--proxy_password", type=str)
parser.add_argument("--aad_client_id", help="AAD client id")
parser.add_argument("--aad_secret", help="AAD secret")
parser.add_argument("--aad_tenant_id", help="AAD tenant id")
parser.add_argument("--storage_acount", default=os.environ["AZURE_STORAGE_ACCOUNT"])
parser.add_argument("--storage_conn_str", help="conn str of storage blob to store ownership and checkpoint data")
parser.add_argument("--storage_container_name", help="storage container name to store ownership and checkpoint data")
parser.add_argument("--pyamqp_logging_enable", help="pyamqp logging enable", action="store_true")
parser.add_argument("--print_console", help="print to console", action="store_true")
parser.add_argument("--log_filename", help="log file name", type=str)
parser.add_argument("--uamqp_mode", help="Flag for uamqp or pyamqp", action="store_true")
parser.add_argument(
    "--debug_level",
    help="Flag for setting a debug level, can be Info, Debug, Warning, Error or Critical",
    type=str,
    default="Error",
)
# rotate logs by default, if you want to disable it, use --no-rotating-logs flag
parser.add_argument("--no-rotating-logs", action="store_true")


args = parser.parse_args()
rotating_logs = not args.no_rotating_logs
starting_position = parse_starting_position(args)
print_console = args.print_console or (os.environ.get("PRINT_CONSOLE") == "1")
debug_level = getattr(logging, args.debug_level.upper(), logging.ERROR)


log_filename = args.log_filename if args.log_filename else "consumer_async"
if args.transport_type == 1:
    log_filename += "_ws.log"
else:
    log_filename += ".log"
logdir = os.environ.get("DEBUG_SHARE")
logfilepath = f"{logdir}/{log_filename}"
LOGGER = get_logger(logfilepath, "stress_receive_async", level=debug_level, print_console=args.print_console, rotating_logs=rotating_logs)
LOG_PER_COUNT = args.output_interval

start_time = time.perf_counter()
recv_cnt_map = defaultdict(int)
recv_cnt_iteration_map = defaultdict(int)
recv_time_map = {}

azure_metric_monitor = AzureMonitorMetric("Async EventHubConsumerClient")


class EventHubConsumerClientTest(EventHubConsumerClient):
    async def get_partition_ids(self):
        if args.partitions != 0:
            return [str(i) for i in range(args.partitions)]
        else:
            return await super(EventHubConsumerClientTest, self).get_partition_ids()


async def on_event_received(process_monitor, partition_context, event):
    recv_cnt_map[partition_context.partition_id] += 1 if event else 0
    if recv_cnt_map[partition_context.partition_id] % LOG_PER_COUNT == 0:
        total_time_elapsed = time.perf_counter() - start_time

        partition_previous_time = recv_time_map.get(partition_context.partition_id)
        partition_current_time = time.perf_counter()
        recv_time_map[partition_context.partition_id] = partition_current_time
        LOGGER.info(
            "Partition: %r, Total received: %r, Time elapsed: %r, Speed since start: %r/s, Current speed: %r/s",
            partition_context.partition_id,
            recv_cnt_map[partition_context.partition_id],
            total_time_elapsed,
            recv_cnt_map[partition_context.partition_id] / total_time_elapsed,
            LOG_PER_COUNT / (partition_current_time - partition_previous_time) if partition_previous_time else None,
        )
        azure_metric_monitor.record_events_cpu_memory(
            LOG_PER_COUNT, process_monitor.cpu_usage_percent, process_monitor.memory_usage_percent
        )
        await partition_context.update_checkpoint(event)


async def on_event_batch_received(process_monitor, partition_context, event_batch):
    recv_cnt_map[partition_context.partition_id] += len(event_batch)
    recv_cnt_iteration_map[partition_context.partition_id] += len(event_batch)
    if recv_cnt_iteration_map[partition_context.partition_id] > LOG_PER_COUNT:
        total_time_elapsed = time.perf_counter() - start_time

        partition_previous_time = recv_time_map.get(partition_context.partition_id)
        partition_current_time = time.perf_counter()
        recv_time_map[partition_context.partition_id] = partition_current_time
        LOGGER.info(
            "Partition: %r, Total received: %r, Time elapsed: %r, Speed since start: %r/s, Current speed: %r/s",
            partition_context.partition_id,
            recv_cnt_map[partition_context.partition_id],
            total_time_elapsed,
            recv_cnt_map[partition_context.partition_id] / total_time_elapsed,
            (
                recv_cnt_iteration_map[partition_context.partition_id]
                / (partition_current_time - partition_previous_time)
                if partition_previous_time
                else None
            ),
        )
        recv_cnt_iteration_map[partition_context.partition_id] = 0
        azure_metric_monitor.record_events_cpu_memory(
            LOG_PER_COUNT, process_monitor.cpu_usage_percent, process_monitor.memory_usage_percent
        )
        await partition_context.update_checkpoint()


async def on_error(partition_context, exception):
    azure_metric_monitor.record_error(exception, extra="partition: {}".format(partition_context.partition_id))


def create_client(args):

    try:
        checkpoint_store = BlobCheckpointStore(
            args.storage_account, DefaultAzureCredential(), args.storage_container_name
        )
    except:
        checkpoint_store = None

    transport_type = TransportType.Amqp if args.transport_type == 0 else TransportType.AmqpOverWebsocket
    http_proxy = None
    if args.proxy_hostname:
        http_proxy = {
            "proxy_hostname": args.proxy_hostname,
            "proxy_port": args.proxy_port,
            "username": args.proxy_username,
            "password": args.proxy_password,
        }

    client = EventHubConsumerClientTest(
        fully_qualified_namespace=args.hostname,
        eventhub_name=args.eventhub,
        consumer_group=args.consumer_group,
        credential=DefaultAzureCredential(),
        checkpoint_store=checkpoint_store,
        load_balancing_interval=args.load_balancing_interval,
        auth_timeout=args.auth_timeout,
        http_proxy=http_proxy,
        transport_type=transport_type,
        logging_enable=args.pyamqp_logging_enable,
        uamqp_transport=args.uamqp_mode,
    )

    return client


async def run(args):

    with ProcessMonitor(
        "monitor_{}".format(args.log_filename), "consumer_stress_async", print_console=args.print_console
    ) as process_monitor:
        kwargs_dict = {
            "prefetch": args.link_credit,
            "partition_id": str(args.recv_partition_id) if args.recv_partition_id else None,
            "track_last_enqueued_event_properties": args.track_last_enqueued_event_properties,
            "starting_position": starting_position,
            "owner_level": args.owner_level,
            "on_error": on_error,
        }
        if args.max_batch_size:
            kwargs_dict["max_batch_size"] = args.max_batch_size
        if args.max_wait_time:
            kwargs_dict["max_wait_time"] = args.max_wait_time

        on_event_received_with_process_monitor = partial(on_event_received, process_monitor)
        on_event_batch_received_with_process_monitor = partial(on_event_batch_received, process_monitor)

        if args.parallel_recv_cnt and args.parallel_recv_cnt > 1:
            clients = [create_client(args) for _ in range(args.parallel_recv_cnt)]
            tasks = [
                asyncio.ensure_future(
                    clients[i].receive_batch(on_event_batch_received_with_process_monitor, **kwargs_dict)
                    if args.max_batch_size
                    else clients[i].receive(on_event_received_with_process_monitor, **kwargs_dict)
                )
                for i in range(args.parallel_recv_cnt)
            ]
        else:
            clients = [create_client(args)]
            tasks = [
                asyncio.ensure_future(
                    clients[0].receive_batch(on_event_batch_received_with_process_monitor, **kwargs_dict)
                    if args.max_batch_size
                    else clients[0].receive(on_event_received_with_process_monitor, **kwargs_dict)
                )
            ]

        await asyncio.sleep(args.duration)
        await asyncio.gather(*[clients[i].close() for i in range(args.parallel_recv_cnt)])
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args))
