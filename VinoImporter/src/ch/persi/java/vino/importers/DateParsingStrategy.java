package ch.persi.java.vino.importers;

import java.time.LocalDate;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class DateParsingStrategy implements DateExtractingStrategy {

	private LocalDate anAuctionDate;
	
	public DateParsingStrategy(String theDateTime) {
		
		Pattern compile = Pattern.compile("([0-9]{2})([0-9]{2})([0-9]{4}).*");
		Matcher matcher = compile.matcher(theDateTime);
		
		if (matcher.matches())
		{
			int year = Integer.parseInt(matcher.group(3));
			int month = Integer.parseInt(matcher.group(2));
			int day = Integer.parseInt(matcher.group(1));
			anAuctionDate = LocalDate.of(year, month, day);
		}
	}
	
	@Override
	public LocalDate getAuctionDate() {
		return anAuctionDate;
	}

}
