# coding: utf-8

# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

"""
FILE: file_samples_directory_async.py

DESCRIPTION:
    These samples demonstrate async directory operations like creating a directory
    or subdirectory, and working on files within the directories.

USAGE:
    python file_samples_directory_async.py

    Set the environment variables with your own values before running the sample:
    1) STORAGE_CONNECTION_STRING - the connection string to your storage account
"""

import asyncio
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
DEST_FILE = os.path.join(current_dir, "SampleDestination.txt")
SOURCE_FILE = os.path.join(current_dir, "SampleSource.txt")


class DirectorySamplesAsync(object):

    connection_string = os.getenv('STORAGE_CONNECTION_STRING')

    async def create_directory_and_file_async(self):
        if self.connection_string is None:
            print("Missing required environment variable: STORAGE_CONNECTION_STRING." + '\n' +
                  "Test: create_directory_and_file_async")
            sys.exit(1)

        # Instantiate the ShareClient from a connection string
        from azure.storage.fileshare.aio import ShareClient
        share = ShareClient.from_connection_string(self.connection_string, "directorysamples1async")

        # Create the share
        async with share:
            await share.create_share()

            try:
                # Get the directory client
                directory = share.get_directory_client(directory_path="mydirectory")

                # [START create_directory]
                await directory.create_directory()
                # [END create_directory]

                # [START upload_file_to_directory]
                # Upload a file to the directory
                with open(SOURCE_FILE, "rb") as source:
                    await directory.upload_file(file_name="sample", data=source)
                # [END upload_file_to_directory]

                # [START delete_file_in_directory]
                # Delete the file in the directory
                await directory.delete_file(file_name="sample")
                # [END delete_file_in_directory]

                # [START delete_directory]
                await directory.delete_directory()
                # [END delete_directory]

            finally:
                # Delete the share
                await share.delete_share()

    async def create_subdirectory_and_file_async(self):
        if self.connection_string is None:
            print("Missing required environment variable: STORAGE_CONNECTION_STRING." + '\n' +
                  "Test: create_subdirectory_and_file_async")
            sys.exit(1)

        # Instantiate the ShareClient from a connection string
        from azure.storage.fileshare.aio import ShareClient
        share = ShareClient.from_connection_string(self.connection_string, "directorysamples2async")

        # Create the share
        async with share:
            await share.create_share()

            try:
                # Get the directory client
                parent_dir = share.get_directory_client(directory_path="parentdir")

                # [START create_subdirectory]
                # Create the directory
                await parent_dir.create_directory()

                # Create a subdirectory
                subdir = await parent_dir.create_subdirectory("subdir")
                # [END create_subdirectory]

                # Upload a file to the parent directory
                with open(SOURCE_FILE, "rb") as source:
                    await parent_dir.upload_file(file_name="sample", data=source)

                # Upload a file to the subdirectory
                with open(SOURCE_FILE, "rb") as source:
                    await subdir.upload_file(file_name="sample", data=source)

                # [START lists_directory]
                # List the directories and files under the parent directory
                my_list = []
                async for item in parent_dir.list_directories_and_files():
                    my_list.append(item)
                print(my_list)
                # [END lists_directory]

                # You must delete the file in the subdirectory before deleting the subdirectory
                await subdir.delete_file("sample")
                # [START delete_subdirectory]
                await parent_dir.delete_subdirectory("subdir")
                # [END delete_subdirectory]

            finally:
                # Delete the share
                await share.delete_share()

    async def get_subdirectory_client_async(self):
        if self.connection_string is None:
            print("Missing required environment variable: STORAGE_CONNECTION_STRING." + '\n' +
                  "Test: get_subdirectory_client_async")
            sys.exit(1)

        # Instantiate the ShareClient from a connection string
        from azure.storage.fileshare.aio import ShareClient
        share = ShareClient.from_connection_string(self.connection_string, "directorysamples3async")

        # Create the share
        async with share:
            await share.create_share()

            try:
                # [START get_subdirectory_client]
                # Get a directory client and create the directory
                parent = share.get_directory_client("dir1")
                await parent.create_directory()

                # Get a subdirectory client and create the subdirectory "dir1/dir2"
                subdirectory = parent.get_subdirectory_client("dir2")
                await subdirectory.create_directory()
                # [END get_subdirectory_client]
            finally:
                # Delete the share
                await share.delete_share()


async def main():
    sample = DirectorySamplesAsync()
    await sample.create_directory_and_file_async()
    await sample.create_subdirectory_and_file_async()
    await sample.get_subdirectory_client_async()

if __name__ == '__main__':
    asyncio.run(main())
