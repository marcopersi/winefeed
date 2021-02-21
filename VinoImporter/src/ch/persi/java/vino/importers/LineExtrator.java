package ch.persi.java.vino.importers;

/**
 * This interface describes the methods which are required to extract a record line from source.
 * At least these methods must be provides, else the record line is unusable respectively not representative.
 */
public interface LineExtrator {

    boolean isRecordLine();

    Integer getVintage();

    boolean isOHK();

    Integer getNoOfBottles();

    Integer getMinPrice();

    Integer getMaxPrice();

    String getWine();

    String getLotNumber();

    Integer getRealizedPrice();

}
