package ch.persi.java.vino.importers;

/**
 * this interface reflects an import strategy. An import is meant as parsing of a qualified source of data.
 */
public interface ImportingStrategy {

    /**
     * executes an import implementation
     */
    default void runImport() {

    }
}
