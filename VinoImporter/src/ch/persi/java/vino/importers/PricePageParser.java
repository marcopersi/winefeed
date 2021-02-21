package ch.persi.java.vino.importers;

import java.util.Map;

/**
 *
 */
public interface PricePageParser {

    /**
     * @param theSource a data structure typically file which should contain the price info.
     * @return a map containing Lot numbers and prices
     */
    Map<Integer, Integer> extractPrices(final String theSource);
}
