#!/bin/bash
docker exec llwfyzhnft87bz6brddiax1z psql -U byos -d byos_ai -c "ALTER TABLE capability_haunt_states ADD COLUMN manifest JSON DEFAULT '{}'::json;"
