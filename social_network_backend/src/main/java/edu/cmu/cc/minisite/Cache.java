package edu.cmu.cc.minisite;

import java.util.HashMap;
import java.util.Map;

/*
 * Wrapper class for cache.
 */
public class Cache {

    /**
     * Internal cache implementation.
     */
    Map<String, String> internalCache = new HashMap<>();

    /**
     * Returns the value to which the specified key is mapped,
     * or null if this cache contains no mapping for the key.
     *
     * @param key the key whose associated value is to be returned
     * @return the value to which the specified key is mapped, or
     *         null if this cache contains no mapping for the key
     */
    public synchronized String get(String key) {
        return internalCache.get(key);
    }

    /**
     * Puts key-value pair in the cache.
     *
     * @param key   key with which the specified value is to be associated
     * @param value value to be associated with the specified key
     */
    public synchronized void put(String key, String value) {
        internalCache.put(key, value);
    }
}
