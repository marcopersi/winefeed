package ch.persi.java.vino.importers.wermuth.prices;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;


import groovy.lang.GroovyClassLoader;
import groovy.lang.GroovyObject;

public class HTMLPricePageExtractor {

	@SuppressWarnings({ "unchecked", "rawtypes" })
	public Map<Integer, Integer> extractPrices(final String theUrl) throws IOException, InstantiationException, IllegalAccessException  {

		Map<Integer, Integer> somePrices = new HashMap<>();
		
		ClassLoader aParent = getClass().getClassLoader();
		try (GroovyClassLoader aLoader =new GroovyClassLoader(aParent))
		{
			final Class aGroovyClass = aLoader.parseClass(new File("src/ch/persi/java/vino/importers/wermuth/prices/GroovyPricePageParser.groovy"));
			
			final GroovyObject aGroovyObject = (GroovyObject) aGroovyClass.newInstance();
			final Object aReturnValue = aGroovyObject.invokeMethod("getRealizedPrices", theUrl);
			
			if (aReturnValue instanceof Map) {
				somePrices = (Map) aReturnValue;
			}
			
		}
		return somePrices;
	}
}
