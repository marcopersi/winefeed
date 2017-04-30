package ch.persi.java.vino.importers;

import java.util.Map;

public interface PricePageParser {
	
	/**
	 * 
	 * @param theSource
	 * @return a map containing Lot numbers and prices
	 */
	Map<Integer, Integer> extractPrices(final String theSource);
}
