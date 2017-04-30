package ch.persi.vino.gui2.client;

import java.util.List;
import java.util.Map;

import ch.persi.vino.gui2.shared.AuctionLot;

import com.google.gwt.user.client.rpc.AsyncCallback;

public interface VinoLotServiceAsync {

	void add(AuctionLot data, AsyncCallback<AuctionLot> callback);

	void fetch(Integer startRow, Integer endRow, String sortBy,
			Map<String, String> filterCriteria,
			AsyncCallback<List<AuctionLot>> callback);

	void remove(AuctionLot data, AsyncCallback<Void> callback);

	void update(AuctionLot data, AsyncCallback<AuctionLot> callback);

}
