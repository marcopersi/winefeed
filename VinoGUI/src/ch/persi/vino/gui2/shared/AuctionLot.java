package ch.persi.vino.gui2.shared;

import com.google.gwt.user.client.rpc.IsSerializable;

public class AuctionLot implements IsSerializable {

	private long id;
	private int lotNumber;
	private String wineName;
	private String owc;
	private int lower;
	private int higher;
	private int gross;
	private int bid;

	
	public long getId() {
		return id;
	}
	public void setId(long id) {
		this.id = id;
	}
	public int getLotNumber() {
		return lotNumber;
	}
	public void setLotNumber(int lotNumber) {
		this.lotNumber = lotNumber;
	}
	public String getWineName() {
		return wineName;
	}
	public void setWineName(String wineName) {
		this.wineName = wineName;
	}
	public String getOwc() {
		return owc;
	}
	public void setOwc(String owc) {
		this.owc = owc;
	}
	public int getLower() {
		return lower;
	}
	public void setLower(int lower) {
		this.lower = lower;
	}
	public int getHigher() {
		return higher;
	}
	public void setHigher(int higher) {
		this.higher = higher;
	}
	public int getGross() {
		return gross;
	}
	public void setGross(int gross) {
		this.gross = gross;
	}
	public int getBid() {
		return bid;
	}
	public void setBid(int bid) {
		this.bid = bid;
	}

	
	
}
