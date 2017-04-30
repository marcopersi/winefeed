package ch.persi.java.vino.importers;

public class Tuple2<T,V> {

	private T key;
	private V value;

	/**
	 * 
	 * @param theKey
	 * @param theValue
	 */
	public Tuple2(final T theKey, final V theValue)
	{
		key=theKey;
		value=theValue;
	}
	
	public T getKey()
	{
		return key;
	}
	
	public V getValue()
	{
		return value;
	}

}
