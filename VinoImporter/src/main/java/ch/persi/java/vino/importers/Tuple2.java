package ch.persi.java.vino.importers;

public class Tuple2<T, V> {

    private final T key;
    private final V value;

    /**
     * @param theKey   the key of the tuple
     * @param theValue the value of the tuple
     */
    public Tuple2(final T theKey, final V theValue) {
        key = theKey;
        value = theValue;
    }

    public T getKey() {
        return key;
    }

    public V getValue() {
        return value;
    }

}
