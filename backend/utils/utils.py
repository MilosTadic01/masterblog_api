import sys
import os
import json
from flask import abort
from typing import List, Dict

DATA_PATH = "data/posts.json"


class Utils:
    """General utilities"""
    @staticmethod
    def load_storage_data():
        """Returns List[Dict], of [] if empty file to start new dataset."""
        if not os.path.exists(DATA_PATH):
            fd = os.open(DATA_PATH, os.O_CREAT)
            os.close(fd)
        with open(DATA_PATH, "r") as fd:
            raw = fd.read()
        if not raw:
            return []
        try:
            blog_posts = json.loads(raw)
        except json.JSONDecodeError as e:
            print(e)
            return []
        return blog_posts

    @staticmethod
    def list_extant_ids():
        """Produce and return a list of unique ids currently in use."""
        list_of_dicts = Utils.load_storage_data()
        list_of_used_ids = [bp_dict.get('id') for bp_dict in list_of_dicts]
        return list_of_used_ids

    @staticmethod
    def get_unique_id():
        """Returns lowest available positive integer not used as id"""
        list_of_used_ids = Utils.list_extant_ids()
        for id_int in range(1, sys.maxsize):
            if id_int not in list_of_used_ids:
                return id_int

    @staticmethod
    def write_data_to_storage(blog_posts: List[Dict]):
        """Dumps and writes List[Dict] of blog posts to storage."""
        with open(DATA_PATH, "w") as fd:
            str_to_write = json.dumps(blog_posts)
            fd.write(str_to_write)

    @staticmethod
    def are_both_int(value1, value2):
        """Return True if both are int, so that I may compare them."""
        return isinstance(value1, int) and isinstance(value2, int)

    @staticmethod
    def are_neither_int(value1, value2):
        """Return True if neither are int, bc in context ==> they are str."""
        return isinstance(value1, str) and isinstance(value2, str)

    @staticmethod
    def validate_sort_query(queries):
        """Could not find ImmutableMultiDict to use as type hint."""
        sorting_crit = None
        sorting_in_rev = None
        if queries:
            for k, v in queries.items(multi=True):
                if k.lower() == "sort":
                    if v.lower() not in ["title", "content"]:
                        abort(400)
                    sorting_crit = v.lower()
                elif k.lower() == "direction":
                    if v.lower() not in ["asc", "desc"]:
                        abort(400)
                    if v.lower() == "desc":
                        sorting_in_rev = True
                    else:
                        sorting_in_rev = False
        return sorting_crit, sorting_in_rev
