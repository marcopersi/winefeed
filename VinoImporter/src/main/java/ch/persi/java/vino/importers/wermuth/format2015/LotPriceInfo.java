package ch.persi.java.vino.importers.wermuth.format2015;

public class LotPriceInfo {

	private final int lowerPrice;
	private final int upperPrice;
	private final int realizedPrice;

	public LotPriceInfo(int theLowerPrice, int theUpperPrice, int theRealizedPrice) {
		lowerPrice = theLowerPrice;
		upperPrice = theUpperPrice;
		realizedPrice = theRealizedPrice;
	}

	public int getLowerPrice() {
		return lowerPrice;
	}

	public int getUpperPrice() {
		return upperPrice;
	}

	public int getRealizedPrice() {
		return realizedPrice;
	}
	
	
	
	@Override
	public int hashCode() {
		final int prime = 31;
		int result = 1;
		result = prime * result + lowerPrice;
		result = prime * result + realizedPrice;
		result = prime * result + upperPrice;
		return result;
	}

	@Override
	public boolean equals(Object obj) {
		if (this == obj)
			return true;
		if (obj == null)
			return false;
		if (getClass() != obj.getClass())
			return false;
		LotPriceInfo other = (LotPriceInfo) obj;
		if (lowerPrice != other.lowerPrice)
			return false;
		if (realizedPrice != other.realizedPrice)
			return false;
		return upperPrice == other.upperPrice;
	}
	
	@Override
	public String toString() {
		StringBuilder builder = new StringBuilder();
		builder.append("LotPriceInfo [lowerPrice=").append(lowerPrice).append(", upperPrice=").append(upperPrice)
				.append(", realizedPrice=").append(realizedPrice).append("]");
		return builder.toString();
	}
	
	
}
