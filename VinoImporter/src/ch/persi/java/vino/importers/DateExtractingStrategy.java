package ch.persi.java.vino.importers;

import java.time.LocalDate;
import java.util.HashMap;
import java.util.Map;

public interface DateExtractingStrategy {

	/**
	 * This API is required to get an auction date. The auction date is a must have attribute to identify an auction and its results.
	 * Since there are various auctioneers the handling how to get or extract an auction date varies very much.
	 * 
	 * @return DateTime
	 */
	LocalDate getAuctionDate();
	
	// Map with months of year, required probably at any date extracting strategy
	Map<String, Integer> MONTHS = new HashMap<String, Integer>() {

		private static final long serialVersionUID = -1653781997868876737L;

		{
			put("Januar", 1);
			put("Februar", 2);
			put("März", 3);
			put("April", 4);
			put("Mai", 5);
			put("Juni", 6);
			put("Juli", 7);
			put("August", 8);
			put("September", 9);
			put("Oktober", 10);
			put("November", 11);
			put("Dezember", 12);
		}
	};

}
