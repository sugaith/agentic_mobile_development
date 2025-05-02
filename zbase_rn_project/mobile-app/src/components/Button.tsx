import { Text, TouchableOpacity } from "react-native";
import { colorPalette } from "../styles/colors";

type ButtonProps = {
  label: string;
};

const Button = ({ label }: ButtonProps) => {
  return (
    <TouchableOpacity
      style={{
        backgroundColor: colorPalette.colorBrand,
        borderRadius: 24,
        padding: 12,
      }}
    >
      <Text style={{ color: "white" }}>{label}</Text>
    </TouchableOpacity>
  );
};

export { Button };
