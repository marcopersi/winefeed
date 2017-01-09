package ch.persi.java.vino.importers;

import java.math.BigDecimal;
import java.math.MathContext;
import java.math.RoundingMode;
import java.util.List;

public interface ImportTask extends Task{

	
	public default BigDecimal determineSize(String theLine)
	{
		if (theLine.contains("3/8")) {
			return new BigDecimal("3.75", new MathContext(0, RoundingMode.HALF_UP));
		} else if (theLine.contains("Magnum")) {
			return new BigDecimal("15", new MathContext(0, RoundingMode.HALF_UP));
		} else if (theLine.contains("Doppel")) {
			return new BigDecimal("30", new MathContext(0, RoundingMode.HALF_UP));
		} else if (theLine.contains("Jeroboam") || theLine.contains("Jéroboam")) {
			return new BigDecimal("45", new MathContext(0, RoundingMode.HALF_UP));
		} else if (theLine.contains("Imperial") || theLine.contains("Impérial") || theLine.contains("Impèrial") ) {
			return new BigDecimal("60", new MathContext(0, RoundingMode.HALF_UP));
		}
		return new BigDecimal("7.5", new MathContext(0, RoundingMode.HALF_UP));
	}
	
	public void saveWineOfferings(List<String> theLines);
}
