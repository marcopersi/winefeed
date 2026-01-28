package ch.persi.vino.gui2.shared;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;

import ch.persi.vino.gui2.client.lib.GenericGwtRpcDataSource;
import ch.persi.vino.gui2.client.lib.GenericGwtRpcService;

import com.google.gwt.user.client.rpc.IsSerializable;

/**
 * Represents a {@link List} for transferring Data Transfer Objects using {@link GenericGwtRpcDataSource} in paged mode.
 * Use it to set totalRows, which will tell your Smart GWT canvas how many rows to except. Set this in the fetch()-method of your {@link GenericGwtRpcService}-implementation.
 * Inherits {@link ArrayList}.
 * 
 * @author Francois Marbot
 *
 * @param <Type> 
 *            type of the transfer object holding the data (will most likely be
 *            a simple POJO), must implement {@link Serializable} or {@link IsSerializable}.
 */
@SuppressWarnings("serial")
public class GenericGwtRpcList<Type> extends ArrayList<Type> {
	
	private Integer totalRows;

	/**
	 * @return Total number of rows available from the server that match the current filter criteria, when using paged result fetching.
	 */
	public Integer getTotalRows() {
		return totalRows;
	}

	/**
	 * Total number of rows available from the server that match the current filter criteria, when using paged result fetching.
	 * Set this in the fetch()-method of your {@link GenericGwtRpcService}-implementation.
	 * 
	 * @param theTotalRows
	 * 	the total number of rows to except.
	 */
	public void setTotalRows(Integer theTotalRows) {
		this.totalRows = theTotalRows;
	}

}
